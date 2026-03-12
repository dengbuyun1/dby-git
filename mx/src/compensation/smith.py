from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import numpy as np

from src.model import PhysiologyModel


@dataclass(frozen=True)
class SmithCompensation:
    predicted_glucose: float
    corrected_glucose: float


class SmithPredictor:
    """Predicts delayed state evolution and outputs virtual-feedback correction."""

    def __init__(self, model: PhysiologyModel, delay_steps: int):
        self.model = model
        self.delay_steps = max(0, int(delay_steps))

    def set_delay_steps(self, delay_steps: int) -> None:
        self.delay_steps = max(0, int(delay_steps))

    def predict_for_control(
        self,
        x_hat: np.ndarray,
        insulin_history_u_per_min: Sequence[float],
        meal_history: Sequence[float],
    ) -> np.ndarray:
        x = np.asarray(x_hat, dtype=float).copy()
        if self.delay_steps == 0:
            return x

        if not insulin_history_u_per_min:
            insulin_history_u_per_min = [0.0]
        if not meal_history:
            meal_history = [0.0]

        u = list(insulin_history_u_per_min)
        m = list(meal_history)

        if len(u) < self.delay_steps:
            u = [u[-1]] * (self.delay_steps - len(u)) + u
        if len(m) < self.delay_steps:
            m = [m[-1]] * (self.delay_steps - len(m)) + m

        u = u[-self.delay_steps :]
        m = m[-self.delay_steps :]

        for ui, mi in zip(u, m):
            x = self.model.step(x, insulin_u_per_min=ui, meal_effect=mi)
        return x

    def compensate_signal(
        self,
        x_hat: np.ndarray,
        insulin_history_u_per_min: Sequence[float],
        meal_history: Sequence[float],
        measured_glucose: float,
    ) -> SmithCompensation:
        """Virtual feedback correction used as controller input.

        corrected_glucose = measured_glucose + (G_pred_delay - G_hat_now)
        """
        x_pred = self.predict_for_control(
            x_hat=x_hat,
            insulin_history_u_per_min=insulin_history_u_per_min,
            meal_history=meal_history,
        )
        g_pred = float(x_pred[0])
        g_hat_now = float(np.asarray(x_hat, dtype=float)[0])
        corrected = float(measured_glucose) + (g_pred - g_hat_now)
        corrected = float(np.clip(corrected, 40.0, 400.0))
        return SmithCompensation(predicted_glucose=g_pred, corrected_glucose=corrected)
