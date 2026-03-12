from __future__ import annotations

import argparse
from pathlib import Path
import sys
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.compensation import SmithPredictor, DelayStepEstimator
from src.config import (
    ControlConfig,
    EKFConfig,
    FaultConfig,
    LoopConfig,
    PhysiologyParams,
    SafetyConfig,
    SBIOnlineConfig,
    SmithConfig,
)
from src.control import PIDInsulinController, SafetySupervisor
from src.estimation import ExtendedKalmanFilter, ResidualFaultDetector
from src.integration import SimglucoseAdapter, RaspberryPiTCPClient
from src.model import PhysiologyModel
from src.sbi_simglucose import SBIOnlineInference
from src.closed_loop import ClosedLoopOrchestrator


def build_system(loop_cfg: LoopConfig, args):
    phys = PhysiologyParams()
    ekf_cfg = EKFConfig()
    fault_cfg = FaultConfig()
    smith_cfg = SmithConfig()
    sbi_cfg = SBIOnlineConfig()
    ctl_cfg = ControlConfig()
    safety_cfg = SafetyConfig()

    env = SimglucoseAdapter(dt_minutes=loop_cfg.dt_minutes, seed=loop_cfg.random_seed)
    actual_dt = int(round(env.sample_time_min)) if env.backend_name == "simglucose" else loop_cfg.dt_minutes

    model = PhysiologyModel(params=phys, dt_minutes=actual_dt)

    x0 = np.array([140.0, 0.0, phys.ib], dtype=float)
    p0 = np.diag([100.0, 0.2, 20.0])
    q = np.diag([ekf_cfg.q_g, ekf_cfg.q_x, ekf_cfg.q_i])
    r = np.array([[ekf_cfg.r_cgm]], dtype=float)

    ekf = ExtendedKalmanFilter(model=model, x0=x0, p0=p0, q=q, r=r)
    delay_steps = int(round(smith_cfg.delay_minutes / max(actual_dt, 1)))
    smith = SmithPredictor(model=model, delay_steps=delay_steps)

    controller = PIDInsulinController(
        target_glucose=ctl_cfg.target_glucose,
        basal_u_per_hr=ctl_cfg.basal_u_per_hr,
        kp=ctl_cfg.kp,
        ki=ctl_cfg.ki,
        kd=ctl_cfg.kd,
        dt_minutes=actual_dt,
    )

    safety = SafetySupervisor(
        min_u_per_hr=safety_cfg.min_u_per_hr,
        max_u_per_hr=safety_cfg.max_u_per_hr,
        hypo_guard_glucose=safety_cfg.hypo_guard_glucose,
        severe_hypo_glucose=safety_cfg.severe_hypo_glucose,
    )

    fault_detector = None
    if not args.disable_fault_detector and fault_cfg.enable:
        fault_detector = ResidualFaultDetector(
            residual_threshold_mg_dl=args.fault_residual_threshold,
            nis_threshold=args.fault_nis_threshold,
            trigger_count=args.fault_trigger_count,
            clear_count=args.fault_clear_count,
        )

    sbi_engine = None
    if args.sbi_enable:
        sbi_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        sbi_engine = SBIOnlineInference(
            model_path=args.sbi_model,
            meta_path=args.sbi_meta,
            posterior_samples=args.sbi_samples,
            device=sbi_device,
            expected_obs_dim=(args.sbi_obs_dim if args.sbi_obs_dim > 0 else None),
        )

    tcp_client = None
    delay_estimator = None

    if args.tcp_enable:
        tcp_client = RaspberryPiTCPClient(
            host=args.tcp_host,
            port=args.tcp_port,
            timeout_sec=args.tcp_timeout,
            connect_timeout_sec=args.tcp_connect_timeout,
        )
        delay_estimator = DelayStepEstimator(
            dt_minutes=actual_dt,
            initial_steps=delay_steps,
            min_steps=args.smith_min_steps,
            max_steps=args.smith_max_steps,
            ema_alpha=args.delay_ema_alpha,
            extra_one_way_delay_ms=args.extra_actuation_delay_ms,
        )

    orchestrator = ClosedLoopOrchestrator(
        env=env,
        ekf=ekf,
        smith=smith,
        controller=controller,
        safety=safety,
        delay_steps=delay_steps,
        tcp_client=tcp_client,
        delay_estimator=delay_estimator,
        fault_detector=fault_detector,
        sbi_engine=sbi_engine,
        sbi_update_interval_steps=max(1, args.sbi_update_interval_steps if args.sbi_update_interval_steps > 0 else sbi_cfg.update_interval_steps),
        tcp_strict=args.tcp_strict,
    )
    return orchestrator, env.backend_name, actual_dt, env.fallback_reason, sbi_engine


def main():
    parser = argparse.ArgumentParser(description="Run simglucose-style closed loop with EKF + Smith compensation")
    parser.add_argument("--steps", type=int, default=180)
    parser.add_argument("--dt-min", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)

    parser.add_argument("--tcp-enable", action="store_true", help="Enable Raspberry Pi TCP actuation channel")
    parser.add_argument("--tcp-host", type=str, default="127.0.0.1")
    parser.add_argument("--tcp-port", type=int, default=19090)
    parser.add_argument("--tcp-timeout", type=float, default=0.5)
    parser.add_argument("--tcp-connect-timeout", type=float, default=1.0)
    parser.add_argument("--tcp-strict", action="store_true", help="Fail immediately if TCP send/recv fails")

    parser.add_argument("--delay-ema-alpha", type=float, default=0.25)
    parser.add_argument("--extra-actuation-delay-ms", type=float, default=0.0)
    parser.add_argument("--smith-min-steps", type=int, default=1)
    parser.add_argument("--smith-max-steps", type=int, default=30)

    parser.add_argument("--disable-fault-detector", action="store_true")
    parser.add_argument("--fault-residual-threshold", type=float, default=25.0)
    parser.add_argument("--fault-nis-threshold", type=float, default=9.0)
    parser.add_argument("--fault-trigger-count", type=int, default=3)
    parser.add_argument("--fault-clear-count", type=int, default=2)

    parser.add_argument("--sbi-enable", action="store_true", help="Enable online SBI parameter updates")
    parser.add_argument("--sbi-model", type=str, default=str(ROOT / "trained_models" / "npe_simglucose.pt"))
    parser.add_argument("--sbi-meta", type=str, default=None)
    parser.add_argument("--sbi-samples", type=int, default=128)
    parser.add_argument("--sbi-obs-dim", type=int, default=0)
    parser.add_argument("--sbi-update-interval-steps", type=int, default=12)

    args = parser.parse_args()

    loop_cfg = LoopConfig(dt_minutes=args.dt_min, steps=args.steps, random_seed=args.seed)
    orchestrator, backend, actual_dt, fallback_reason, sbi_engine = build_system(loop_cfg, args)

    df = orchestrator.run(steps=loop_cfg.steps)

    out_dir = ROOT / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "closed_loop_log.csv"
    df.to_csv(out_file, index=False)

    print(f"Backend: {backend}")
    print(f"EKF/Smith dt(min): {actual_dt}")
    print(f"TCP enabled: {args.tcp_enable}")
    print(f"Fault detector enabled: {not args.disable_fault_detector}")
    print(f"SBI enabled: {args.sbi_enable}")
    if sbi_engine is not None and (not sbi_engine.enabled):
        print(f"SBI disabled reason: {sbi_engine.disabled_reason}")
    if backend == "mock" and fallback_reason:
        print(f"Fallback reason: {fallback_reason}")
    print(f"Saved: {out_file}")
    if not df.empty:
        alarm_count = int(df["fault_alarm"].sum()) if "fault_alarm" in df.columns else 0
        mean_abs_residual = float(df["residual_abs"].mean()) if "residual_abs" in df.columns else float("nan")
        sbi_updates = int(df["sbi_updated"].sum()) if "sbi_updated" in df.columns else 0
        print(
            "Summary: "
            f"mean_CGM={df['cgm'].mean():.2f}, "
            f"min_CGM={df['cgm'].min():.2f}, "
            f"max_CGM={df['cgm'].max():.2f}, "
            f"mean_insulin={df['insulin_applied_u_per_hr'].mean():.2f} U/hr, "
            f"alarm_steps={alarm_count}, "
            f"mean_abs_residual={mean_abs_residual:.2f}, "
            f"sbi_updates={sbi_updates}"
        )


if __name__ == "__main__":
    main()
