from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from src.model import PhysiologyModel


@dataclass(frozen=True)
class EKFDiagnostics:
    predicted_measurement: float
    innovation: float
    innovation_abs: float
    innovation_var: float
    nis: float


class ExtendedKalmanFilter:
    def __init__(
        self,
        model: PhysiologyModel,
        x0: np.ndarray,
        p0: np.ndarray,
        q: np.ndarray,
        r: np.ndarray,
    ):
        self.model = model
        self.x = np.asarray(x0, dtype=float).reshape(3)
        self.p = np.asarray(p0, dtype=float).reshape(3, 3)
        self.q = np.asarray(q, dtype=float).reshape(3, 3)
        self.r = np.asarray(r, dtype=float).reshape(1, 1)
        self._last_diag = EKFDiagnostics(
            predicted_measurement=float(self.x[0]),
            innovation=0.0,
            innovation_abs=0.0,
            innovation_var=float(self.r[0, 0]),
            nis=0.0,
        )

    def predict(self, insulin_u_per_min: float, meal_effect: float = 0.0) -> np.ndarray:
        f = self.model.jacobian_f(self.x)
        self.x = self.model.step(self.x, insulin_u_per_min=insulin_u_per_min, meal_effect=meal_effect)
        self.p = f @ self.p @ f.T + self.q
        self.p = 0.5 * (self.p + self.p.T)
        return self.x.copy()

    def update(self, cgm_mg_dl: float) -> np.ndarray:
        z = float(cgm_mg_dl)
        h = self.model.jacobian_h()

        z_pred = float(self.model.h(self.x)[0])
        innovation = z - z_pred

        s = float((h @ self.p @ h.T + self.r)[0, 0])
        s = max(s, 1e-9)
        k = (self.p @ h.T) / s

        self.x = self.x + (k.reshape(3) * innovation)

        i = np.eye(3)
        self.p = (i - k @ h) @ self.p @ (i - k @ h).T + k @ self.r @ k.T
        self.p = 0.5 * (self.p + self.p.T)

        nis = (innovation * innovation) / s
        self._last_diag = EKFDiagnostics(
            predicted_measurement=z_pred,
            innovation=innovation,
            innovation_abs=abs(innovation),
            innovation_var=s,
            nis=nis,
        )
        return self.x.copy()

    @property
    def state(self) -> np.ndarray:
        return self.x.copy()

    @property
    def diagnostics(self) -> EKFDiagnostics:
        return self._last_diag
