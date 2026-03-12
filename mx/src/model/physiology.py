from __future__ import annotations

import numpy as np

from src.config import PhysiologyParams


class PhysiologyModel:
    """Simple nonlinear glucose-insulin model for estimator/predictor internals.

    State x = [G, X, I]
    - G: plasma glucose (mg/dL)
    - X: insulin action (1/min)
    - I: plasma insulin proxy (arb. units)
    """

    def __init__(self, params: PhysiologyParams, dt_minutes: float = 5.0):
        self.params = params
        self.dt = float(dt_minutes)

        # Keep nominal values so online adaptation scales from a stable baseline.
        self._nominal_p1 = float(params.p1)
        self._nominal_p2 = float(params.p2)
        self._nominal_p3 = float(params.p3)
        self._nominal_meal_gain = 1.0

        self.meal_gain = 1.0
        self.last_sbi_scales: dict[str, float] = {
            "kabs": 1.0,
            "kp1": 1.0,
            "kp2": 1.0,
            "kp3": 1.0,
        }

    @staticmethod
    def _clip_scale(v: float, lo: float = 0.5, hi: float = 2.0) -> float:
        return float(min(max(float(v), lo), hi))

    def apply_sbi_scales(self, scales: dict[str, float]) -> dict[str, float]:
        """Apply SBI inferred scales to internal dynamics.

        Mapping used in this scaffold:
        - kp1 -> p1
        - kp2 -> p2
        - kp3 -> p3
        - kabs -> meal disturbance gain
        """
        kp1 = self._clip_scale(scales.get("kp1", 1.0))
        kp2 = self._clip_scale(scales.get("kp2", 1.0))
        kp3 = self._clip_scale(scales.get("kp3", 1.0))
        kabs = self._clip_scale(scales.get("kabs", 1.0))

        self.params.p1 = self._nominal_p1 * kp1
        self.params.p2 = self._nominal_p2 * kp2
        self.params.p3 = self._nominal_p3 * kp3
        self.meal_gain = self._nominal_meal_gain * kabs

        self.last_sbi_scales = {
            "kabs": kabs,
            "kp1": kp1,
            "kp2": kp2,
            "kp3": kp3,
        }
        return dict(self.last_sbi_scales)

    def step(self, x: np.ndarray, insulin_u_per_min: float, meal_effect: float = 0.0) -> np.ndarray:
        p = self.params
        g, xa, ins = np.asarray(x, dtype=float)

        insulin_input = insulin_u_per_min * 1000.0 / max(p.body_weight_kg, 1e-6)

        d_ins = -p.n * (ins - p.ib) + insulin_input / max(p.vi, 1e-6)
        d_xa = -p.p2 * xa + p.p3 * (ins - p.ib)

        glucose_drive = max(g - 40.0, 0.0)
        d_g = -p.p1 * (g - p.gb) - max(xa, 0.0) * glucose_drive + self.meal_gain * meal_effect

        g_next = max(40.0, g + self.dt * d_g)
        xa_next = xa + self.dt * d_xa
        ins_next = max(0.0, ins + self.dt * d_ins)

        return np.array([g_next, xa_next, ins_next], dtype=float)

    def h(self, x: np.ndarray) -> np.ndarray:
        return np.array([float(x[0])], dtype=float)

    def jacobian_f(self, x: np.ndarray) -> np.ndarray:
        p = self.params
        g, xa, _ = np.asarray(x, dtype=float)

        dgdg = 1.0 + self.dt * (-p.p1 - (max(xa, 0.0) if g > 40.0 else 0.0))
        dgdx = self.dt * (-max(g - 40.0, 0.0))
        dgdi = 0.0

        dxdg = 0.0
        dxdx = 1.0 - self.dt * p.p2
        dxdi = self.dt * p.p3

        didg = 0.0
        didx = 0.0
        didi = 1.0 - self.dt * p.n

        return np.array(
            [
                [dgdg, dgdx, dgdi],
                [dxdg, dxdx, dxdi],
                [didg, didx, didi],
            ],
            dtype=float,
        )

    @staticmethod
    def jacobian_h() -> np.ndarray:
        return np.array([[1.0, 0.0, 0.0]], dtype=float)
