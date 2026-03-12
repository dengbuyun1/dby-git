"""
Zone-MPC controller for simglucose with hypo-averse behavior.

- Target glucose: 140 mg/dL
- Zone: lower = 30 mg/dL, upper = 180 mg/dL
- Stronger penalties and hard constraint to avoid hypoglycemia; willing to stay above 180 longer.
- Only basal modulation (no bolus).
"""

from __future__ import annotations

import logging
from typing import Optional

import cvxpy as cp
import numpy as np
from simglucose.controller.base import Action, Controller

LOGGER = logging.getLogger(__name__)


class ZoneMPCController(Controller):
    """Simple zone-MPC with asymmetric penalties (low > high)."""

    def __init__(
        self,
        target: float = 140.0,
        g_lower: float = 30.0,
        g_upper: float = 180.0,
        g_safety: float = 90.0,
        basal_rate: float = 0.015,
        sample_time_min: float = 5.0,
        pred_horizon_min: float = 120.0,
        control_horizon_min: float = 45.0,
        u_min: float = -0.02,
        u_max: float = 0.04,
        w_under: float = 80.0,
        w_over: float = 2.0,
        r_u: float = 0.05,
        r_du: float = 4.0,
    ) -> None:
        super().__init__(init_state=None)
        self.target = float(target)
        self.g_lower = float(g_lower)
        self.g_upper = float(g_upper)
        self.g_safety = float(g_safety)
        self.basal_rate = float(basal_rate)  # U/min
        self.sample_time_min = float(sample_time_min)
        self.pred_horizon_min = float(pred_horizon_min)
        self.control_horizon_min = float(control_horizon_min)
        self.u_min = float(u_min)
        self.u_max = float(u_max)
        self.w_under = float(w_under)
        self.w_over = float(w_over)
        self.r_u = float(r_u)
        self.r_du = float(r_du)

        # Internal state: [glucose_deviation, insulin_action]
        self.state = np.zeros(2, dtype=float)
        self.last_u = 0.0  # previous correction (U/min)

        # Nominal dynamics (heuristic) expressed for 5 min step
        self.base_dt_min = 5.0
        self.base_glucose_decay = 0.98
        self.base_insulin_decay = 0.85
        self.base_coupling = 1.0
        self.base_insulin_sensitivity = 8.0

        self._update_model(self.sample_time_min)

    # ------------------------------------------------------------------ #
    # Model helpers
    # ------------------------------------------------------------------ #
    def _update_model(self, sample_time_min: float) -> None:
        """Recompute discrete model matrices when the sample time changes."""
        dt_ratio = float(sample_time_min / self.base_dt_min)
        g_decay = self.base_glucose_decay**dt_ratio
        i_decay = self.base_insulin_decay**dt_ratio
        coupling = self.base_coupling * dt_ratio
        sens = self.base_insulin_sensitivity * dt_ratio

        # x = [g_dev, insulin_action]; u is correction in U/min
        self.A = np.array([[g_decay, coupling], [0.0, i_decay]], dtype=float)
        self.B = np.array([[0.0], [-sens]], dtype=float)

        self.sample_time_min = float(sample_time_min)
        self.pred_steps = max(
            4, int(round(self.pred_horizon_min / self.sample_time_min))
        )
        self.control_steps = max(
            2, int(round(self.control_horizon_min / self.sample_time_min))
        )

    # ------------------------------------------------------------------ #
    # MPC solver
    # ------------------------------------------------------------------ #
    def _solve_mpc(self, g_dev: float) -> Optional[float]:
        """
        Solve the zone-MPC QP and return the first control move (U/min).
        Returns None on solver failure.
        """
        Hp = self.pred_steps
        Hu = self.control_steps
        nx = 2

        x = cp.Variable((nx, Hp + 1))
        u = cp.Variable(Hu)

        constraints = [x[:, 0] == np.array([g_dev, self.state[1]], dtype=float)]
        cost_terms = []

        for k in range(Hp):
            u_k = u[min(k, Hu - 1)]

            constraints.append(u_k >= self.u_min)
            constraints.append(u_k <= self.u_max)

            constraints.append(x[:, k + 1] == self.A @ x[:, k] + self.B.flatten() * u_k)

            g_pred = self.target + x[0, k + 1]

            # Hard safety: do not predict below g_safety
            constraints.append(g_pred >= self.g_safety)

            # Zone penalties (asymmetric)
            over = cp.pos(g_pred - self.g_upper)
            under = cp.pos(self.g_lower - g_pred)
            cost_terms.append(self.w_over * cp.sum_squares(over))
            cost_terms.append(self.w_under * cp.sum_squares(under))

            # Input cost
            cost_terms.append(self.r_u * cp.sum_squares(u_k))

            # Move suppression
            prev = self.last_u if k == 0 else u[min(k - 1, Hu - 1)]
            cost_terms.append(self.r_du * cp.sum_squares(u_k - prev))

        problem = cp.Problem(cp.Minimize(cp.sum(cost_terms)), constraints)

        try:
            problem.solve(solver=cp.OSQP, warm_start=True, max_iter=4000)
        except Exception as exc:  # pragma: no cover - solver guard
            LOGGER.debug("Zone-MPC solve failed: %s", exc)
            return None

        if problem.status not in ("optimal", "optimal_inaccurate"):
            LOGGER.debug("Zone-MPC status: %s", problem.status)
            return None
        if u.value is None:
            return None

        return float(u.value[0])

    # ------------------------------------------------------------------ #
    # Controller API
    # ------------------------------------------------------------------ #
    def policy(self, observation, reward, done, **info) -> Action:
        if done:
            return Action(basal=0.0, bolus=0.0)

        sample_time = float(info.get("sample_time", self.sample_time_min))
        if abs(sample_time - self.sample_time_min) > 1e-6:
            self._update_model(sample_time)

        current_glucose = float(observation.CGM)
        g_dev = current_glucose - self.target

        # Hypo safety: suspend early
        if current_glucose <= self.g_safety:
            self.last_u = -self.basal_rate
            self.state = np.array([g_dev, 0.0], dtype=float)
            return Action(basal=0.0, bolus=0.0)

        # Reset model state glucose component with latest measurement
        self.state[0] = g_dev

        u_correction = self._solve_mpc(g_dev)
        if u_correction is None:
            u_correction = 0.0

        # If currently below target, do not allow more insulin (clip toward suspend)
        if current_glucose < self.target:
            u_correction = min(u_correction, 0.0)

        # Propagate internal state for warm start
        self.state = self.A @ self.state + self.B.flatten() * u_correction
        self.last_u = u_correction

        basal_out = max(0.0, self.basal_rate + u_correction)
        return Action(basal=basal_out, bolus=0.0)

    def reset(self) -> None:
        self.state = np.zeros(2, dtype=float)
        self.last_u = 0.0
