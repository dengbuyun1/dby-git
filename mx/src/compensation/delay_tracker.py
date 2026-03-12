from __future__ import annotations


class DelayStepEstimator:
    """Estimate Smith delay steps from measured transport delay (RTT)."""

    def __init__(
        self,
        dt_minutes: float,
        initial_steps: int,
        min_steps: int = 0,
        max_steps: int = 30,
        ema_alpha: float = 0.25,
        extra_one_way_delay_ms: float = 0.0,
    ):
        self.dt_minutes = max(float(dt_minutes), 1e-6)
        self.min_steps = int(min_steps)
        self.max_steps = int(max_steps)
        self.ema_alpha = float(ema_alpha)
        self.extra_one_way_delay_ms = float(extra_one_way_delay_ms)

        self._delay_steps = int(initial_steps)
        self._one_way_ms_ema = self._delay_steps * self.dt_minutes * 60_000.0

    @property
    def delay_steps(self) -> int:
        return self._delay_steps

    def update_from_rtt_ms(self, rtt_ms: float | None) -> int:
        if rtt_ms is None:
            return self._delay_steps

        rtt_ms = max(float(rtt_ms), 0.0)
        one_way_ms = 0.5 * rtt_ms + self.extra_one_way_delay_ms

        self._one_way_ms_ema = self.ema_alpha * one_way_ms + (1.0 - self.ema_alpha) * self._one_way_ms_ema
        est_steps = int(round((self._one_way_ms_ema / 60_000.0) / self.dt_minutes))
        est_steps = max(self.min_steps, min(self.max_steps, est_steps))

        self._delay_steps = est_steps
        return self._delay_steps
