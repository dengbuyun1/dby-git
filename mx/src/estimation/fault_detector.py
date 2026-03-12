from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FaultStatus:
    is_alarm: bool
    triggered: bool
    cleared: bool
    reason: str
    residual: float
    abs_residual: float
    nis: float
    consecutive_violations: int
    consecutive_normals: int


class ResidualFaultDetector:
    """Simple fault logic using EKF residual and NIS thresholds."""

    def __init__(
        self,
        residual_threshold_mg_dl: float = 25.0,
        nis_threshold: float = 9.0,
        trigger_count: int = 3,
        clear_count: int = 2,
    ):
        if trigger_count < 1:
            raise ValueError("trigger_count must be >= 1")
        if clear_count < 1:
            raise ValueError("clear_count must be >= 1")

        self.residual_threshold_mg_dl = float(residual_threshold_mg_dl)
        self.nis_threshold = float(nis_threshold)
        self.trigger_count = int(trigger_count)
        self.clear_count = int(clear_count)

        self._alarm_latched = False
        self._violation_count = 0
        self._normal_count = 0

    @property
    def alarm_latched(self) -> bool:
        return self._alarm_latched

    @staticmethod
    def neutral_status() -> FaultStatus:
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

    def update(self, residual: float, nis: float) -> FaultStatus:
        residual = float(residual)
        abs_residual = abs(residual)
        nis = float(nis)

        over_residual = abs_residual >= self.residual_threshold_mg_dl
        over_nis = nis >= self.nis_threshold
        violation = over_residual or over_nis

        if violation:
            self._violation_count += 1
            self._normal_count = 0
        else:
            self._normal_count += 1
            self._violation_count = 0

        triggered = False
        cleared = False

        if violation and self._violation_count >= self.trigger_count:
            if not self._alarm_latched:
                triggered = True
            self._alarm_latched = True

        if self._alarm_latched and (not violation) and self._normal_count >= self.clear_count:
            self._alarm_latched = False
            cleared = True

        if self._alarm_latched:
            reason_parts = []
            if over_residual:
                reason_parts.append("residual")
            if over_nis:
                reason_parts.append("nis")
            reason = "+".join(reason_parts) if reason_parts else "latched"
        elif cleared:
            reason = "cleared"
        else:
            reason = "normal"

        return FaultStatus(
            is_alarm=self._alarm_latched,
            triggered=triggered,
            cleared=cleared,
            reason=reason,
            residual=residual,
            abs_residual=abs_residual,
            nis=nis,
            consecutive_violations=self._violation_count,
            consecutive_normals=self._normal_count,
        )
