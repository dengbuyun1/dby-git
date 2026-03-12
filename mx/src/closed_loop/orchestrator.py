from __future__ import annotations

from collections import deque
from dataclasses import dataclass, asdict
import pandas as pd

from src.compensation import SmithPredictor, DelayStepEstimator
from src.control import PIDInsulinController, SafetySupervisor
from src.estimation import ExtendedKalmanFilter, ResidualFaultDetector, FaultStatus
from src.integration import SimglucoseAdapter, RaspberryPiTCPClient
from src.sbi_simglucose import SBIOnlineInference


@dataclass
class LoopRecord:
    step: int
    cgm: float
    sbi_updated: bool
    sbi_status: str
    sbi_scale_kabs: float
    sbi_scale_kp1: float
    sbi_scale_kp2: float
    sbi_scale_kp3: float
    ekf_g_model: float
    residual: float
    residual_abs: float
    residual_nis: float
    fault_alarm: bool
    fault_reason: str
    xhat_g: float
    xhat_x: float
    xhat_i: float
    smith_predicted_glucose: float
    controller_input_glucose: float
    insulin_raw_u_per_hr: float
    fault_override_active: bool
    insulin_safe_u_per_hr: float
    insulin_applied_u_per_hr: float
    meal_effect: float
    tcp_rtt_ms: float | None
    smith_delay_steps: int
    actuation_source: str


class ClosedLoopOrchestrator:
    """Flow: Observation -> EKF -> FaultLogic -> Smith -> Controller -> Safety -> Actuation."""

    def __init__(
        self,
        env: SimglucoseAdapter,
        ekf: ExtendedKalmanFilter,
        smith: SmithPredictor,
        controller: PIDInsulinController,
        safety: SafetySupervisor,
        delay_steps: int,
        tcp_client: RaspberryPiTCPClient | None = None,
        delay_estimator: DelayStepEstimator | None = None,
        fault_detector: ResidualFaultDetector | None = None,
        sbi_engine: SBIOnlineInference | None = None,
        sbi_update_interval_steps: int = 12,
        tcp_strict: bool = False,
    ):
        self.env = env
        self.ekf = ekf
        self.smith = smith
        self.controller = controller
        self.safety = safety
        self.delay_steps = max(0, int(delay_steps))
        self.tcp_client = tcp_client
        self.delay_estimator = delay_estimator
        self.fault_detector = fault_detector
        self.sbi_engine = sbi_engine
        self.sbi_update_interval_steps = max(1, int(sbi_update_interval_steps))
        self.tcp_strict = bool(tcp_strict)

        self.u_hist = deque(maxlen=max(1, self.delay_steps))
        self.m_hist = deque(maxlen=max(1, self.delay_steps))
        self.cgm_hist: list[float] = []

    def _resize_histories(self, new_delay_steps: int) -> None:
        new_delay_steps = max(0, int(new_delay_steps))
        old_u = list(self.u_hist)
        old_m = list(self.m_hist)

        maxlen = max(1, new_delay_steps)
        self.u_hist = deque(old_u[-maxlen:], maxlen=maxlen)
        self.m_hist = deque(old_m[-maxlen:], maxlen=maxlen)

        if not self.u_hist:
            self.u_hist.append(self.controller.basal_u_per_hr / 60.0)
        if not self.m_hist:
            self.m_hist.append(0.0)

        self.delay_steps = new_delay_steps
        self.smith.set_delay_steps(new_delay_steps)

    def _apply_with_tcp(self, safe_u_hr: float, step: int, cgm: float) -> tuple[float, float | None, str]:
        if self.tcp_client is None:
            return safe_u_hr, None, "local"

        try:
            res = self.tcp_client.send_insulin(insulin_u_per_hr=safe_u_hr, step=step, glucose=cgm)
            return float(res.applied_u_per_hr), res.rtt_ms, res.source
        except Exception:
            if self.tcp_strict:
                raise
            return safe_u_hr, None, "tcp_fallback_local"

    @staticmethod
    def _neutral_fault_status() -> FaultStatus:
        return FaultStatus(
            is_alarm=False,
            triggered=False,
            cleared=False,
            reason="disabled",
            residual=0.0,
            abs_residual=0.0,
            nis=0.0,
            consecutive_violations=0,
            consecutive_normals=0,
        )

    def _sbi_scales_snapshot(self) -> dict[str, float]:
        model = self.ekf.model
        scales = getattr(model, "last_sbi_scales", None)
        if not isinstance(scales, dict):
            return {"kabs": 1.0, "kp1": 1.0, "kp2": 1.0, "kp3": 1.0}
        return {
            "kabs": float(scales.get("kabs", 1.0)),
            "kp1": float(scales.get("kp1", 1.0)),
            "kp2": float(scales.get("kp2", 1.0)),
            "kp3": float(scales.get("kp3", 1.0)),
        }

    def _maybe_update_sbi(self, step: int) -> tuple[bool, str]:
        if self.sbi_engine is None:
            return False, "disabled"
        if not self.sbi_engine.enabled:
            return False, self.sbi_engine.disabled_reason
        if step % self.sbi_update_interval_steps != 0:
            return False, "skip_interval"

        res = self.sbi_engine.infer_scales(self.cgm_hist)
        if res is None:
            return False, "insufficient_history"
        if not res.scales:
            return False, res.status

        self.ekf.model.apply_sbi_scales(res.scales)
        if self.smith.model is not self.ekf.model:
            self.smith.model.apply_sbi_scales(res.scales)
        return True, res.status

    def run(self, steps: int) -> pd.DataFrame:
        first = self.env.reset()
        cgm = float(first.cgm)
        meal = float(first.meal_effect)

        basal = self.controller.basal_u_per_hr
        for _ in range(max(1, self.delay_steps)):
            self.u_hist.append(basal / 60.0)
            self.m_hist.append(0.0)

        records = []

        for k in range(int(steps)):
            self.cgm_hist.append(float(cgm))
            sbi_updated, sbi_status = self._maybe_update_sbi(k)
            scales = self._sbi_scales_snapshot()

            applied_u_per_min = self.u_hist[-1]
            self.ekf.predict(insulin_u_per_min=applied_u_per_min, meal_effect=meal)
            xhat = self.ekf.update(cgm)
            diag = self.ekf.diagnostics

            if self.fault_detector is None:
                fault = self._neutral_fault_status()
            else:
                fault = self.fault_detector.update(residual=diag.innovation, nis=diag.nis)

            smith_out = self.smith.compensate_signal(
                x_hat=xhat,
                insulin_history_u_per_min=list(self.u_hist),
                meal_history=list(self.m_hist),
                measured_glucose=cgm,
            )
            controller_input_glucose = smith_out.corrected_glucose

            raw_u_hr = self.controller.compute_u_per_hr(predicted_glucose=controller_input_glucose)

            fault_override_active = bool(fault.is_alarm)
            if fault_override_active:
                raw_u_hr = self.safety.min_u_per_hr

            safe_u_hr = self.safety.filter_u_per_hr(
                raw_u_per_hr=raw_u_hr,
                current_glucose=cgm,
                predicted_glucose=smith_out.predicted_glucose,
            )

            measured_u_hr, rtt_ms, source = self._apply_with_tcp(safe_u_hr, step=k, cgm=cgm)

            if self.delay_estimator is not None:
                new_steps = self.delay_estimator.update_from_rtt_ms(rtt_ms)
                if new_steps != self.delay_steps:
                    self._resize_histories(new_steps)

            out = self.env.step(insulin_u_per_hr=measured_u_hr)

            records.append(
                LoopRecord(
                    step=k,
                    cgm=cgm,
                    sbi_updated=sbi_updated,
                    sbi_status=sbi_status,
                    sbi_scale_kabs=scales["kabs"],
                    sbi_scale_kp1=scales["kp1"],
                    sbi_scale_kp2=scales["kp2"],
                    sbi_scale_kp3=scales["kp3"],
                    ekf_g_model=float(diag.predicted_measurement),
                    residual=float(diag.innovation),
                    residual_abs=float(diag.innovation_abs),
                    residual_nis=float(diag.nis),
                    fault_alarm=bool(fault.is_alarm),
                    fault_reason=fault.reason,
                    xhat_g=float(xhat[0]),
                    xhat_x=float(xhat[1]),
                    xhat_i=float(xhat[2]),
                    smith_predicted_glucose=float(smith_out.predicted_glucose),
                    controller_input_glucose=float(controller_input_glucose),
                    insulin_raw_u_per_hr=float(raw_u_hr),
                    fault_override_active=fault_override_active,
                    insulin_safe_u_per_hr=float(safe_u_hr),
                    insulin_applied_u_per_hr=float(measured_u_hr),
                    meal_effect=meal,
                    tcp_rtt_ms=rtt_ms,
                    smith_delay_steps=self.delay_steps,
                    actuation_source=source,
                )
            )

            self.u_hist.append(measured_u_hr / 60.0)
            self.m_hist.append(float(out.meal_effect))

            cgm = float(out.cgm)
            meal = float(out.meal_effect)

            if out.done:
                break

        if self.tcp_client is not None:
            self.tcp_client.close()

        return pd.DataFrame([asdict(r) for r in records])
