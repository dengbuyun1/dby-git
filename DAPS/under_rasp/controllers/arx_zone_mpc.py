"""
ARX + RLS (variable forgetting) zone-MPC controller for simglucose.

- Online ARX identification with RLS + VFF updates (4 params: a1, a2, b1, b2)
- Zone-MPC cost: heavy penalty on low glucose, light penalty on high
- Target glucose: 140 mg/dL; acceptable zone 30–180 mg/dL; safety floor 90 mg/dL
- Only modulates basal (no bolus). If blood glucose is low, it suspends insulin.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import cvxpy as cp
import numpy as np
from simglucose.actuator.pump import InsulinPump
from simglucose.controller.base import Action, Controller
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.env import T1DSimEnv
from simglucose.simulation.scenario import CustomScenario

LOGGER = logging.getLogger(__name__)


class ARXRLSZoneMPCController(Controller):
    """
    Zone-MPC with online ARX model identification (RLS + variable forgetting factor).
    Low-glucose avoidance is prioritized over quick correction of high glucose.
    """

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
        w_under: float = 120.0,
        w_over: float = 1.5,
        r_u: float = 0.05,
        r_du: float = 4.0,
    ) -> None:
        super().__init__(init_state=None)
        self.target = float(target)
        self.g_lower = float(g_lower)
        self.g_upper = float(g_upper)
        self.g_safety = float(g_safety)
        self.basal_rate = float(basal_rate)
        self.sample_time_min = float(sample_time_min)
        self.pred_horizon_min = float(pred_horizon_min)
        self.control_horizon_min = float(control_horizon_min)
        self.u_min = float(u_min)
        self.u_max = float(u_max)
        self.w_under = float(w_under)
        self.w_over = float(w_over)
        self.r_u = float(r_u)
        self.r_du = float(r_du)

        # RLS parameters (theta = [a1, a2, b1, b2])
        self.theta = np.array([0.9, -0.05, -0.8, -0.2], dtype=float)
        self.P = np.eye(4) * 500.0
        self.lam_base = 0.98
        self.lam_min = 0.95
        self.lam_max = 0.999
        self.kappa = 0.02
        self.err_ref = 40.0

        # History for ARX lags
        self.prev_y1 = 0.0  # y(k-1)
        self.prev_y2 = 0.0  # y(k-2)
        self.prev_u1 = 0.0  # u(k-1)
        self.prev_u2 = 0.0  # u(k-2)

        self.pred_steps = max(
            4, int(round(self.pred_horizon_min / self.sample_time_min))
        )
        self.control_steps = max(
            2, int(round(self.control_horizon_min / self.sample_time_min))
        )

    # ------------------------------------------------------------------ #
    # RLS update with variable forgetting factor
    # ------------------------------------------------------------------ #
    def _update_rls(self, y_meas: float) -> None:
        phi = np.array(
            [self.prev_y1, self.prev_y2, self.prev_u1, self.prev_u2], dtype=float
        )
        y_hat = float(phi @ self.theta)
        err = y_meas - y_hat

        # Variable forgetting factor: increase forgetting on large residuals
        lam = self.lam_base + self.kappa * min(1.0, abs(err) / self.err_ref)
        lam = float(np.clip(lam, self.lam_min, self.lam_max))

        denom = lam + phi @ self.P @ phi
        if denom <= 0:
            return

        K = (self.P @ phi) / denom
        self.theta = self.theta + K * err
        self.P = (self.P - np.outer(K, phi) @ self.P) / lam

    # ------------------------------------------------------------------ #
    # MPC solver on current ARX model
    # ------------------------------------------------------------------ #
    def _solve_mpc(self, y_curr: float) -> Optional[float]:
        Hp = self.pred_steps
        Hu = self.control_steps

        a1, a2, b1, b2 = self.theta
        y = cp.Variable(Hp + 1)
        u = cp.Variable(Hu)

        constraints = [y[0] == y_curr]
        cost_terms = []

        for k in range(Hp):
            u_curr = u[k] if k < Hu else u[Hu - 1]
            u_prev = self.prev_u1 if k == 0 else u[k - 1 if k - 1 < Hu else Hu - 1]
            y_prev = self.prev_y1 if k == 0 else y[k - 1]

            # ARX rollout: y(k+1) = a1*y(k) + a2*y(k-1) + b1*u(k) + b2*u(k-1)
            y_next = a1 * y[k] + a2 * y_prev + b1 * u_curr + b2 * u_prev
            constraints.append(y[k + 1] == y_next)

            constraints.append(u_curr >= self.u_min)
            constraints.append(u_curr <= self.u_max)

            g_pred = self.target + y[k + 1]

            # Safety floor
            constraints.append(g_pred >= self.g_safety)

            over = cp.pos(g_pred - self.g_upper)
            under = cp.pos(self.g_lower - g_pred)
            cost_terms.append(self.w_over * cp.sum_squares(over))
            cost_terms.append(self.w_under * cp.sum_squares(under))

            # Input penalties
            cost_terms.append(self.r_u * cp.sum_squares(u_curr))
            prev_for_du = self.prev_u1 if k == 0 else u[k - 1 if k - 1 < Hu else Hu - 1]
            cost_terms.append(self.r_du * cp.sum_squares(u_curr - prev_for_du))

        problem = cp.Problem(cp.Minimize(cp.sum(cost_terms)), constraints)

        try:
            problem.solve(solver=cp.OSQP, warm_start=True, max_iter=4000)
        except Exception as exc:  # pragma: no cover
            LOGGER.debug("ARX zone-MPC solve failed: %s", exc)
            return None

        if problem.status not in ("optimal", "optimal_inaccurate"):
            LOGGER.debug("ARX zone-MPC status: %s", problem.status)
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

        current_glucose = float(observation.CGM)
        y_curr = current_glucose - self.target

        # Hard hypo protection
        if current_glucose <= self.g_safety:
            self._shift_histories(y_curr, -self.basal_rate)
            return Action(basal=0.0, bolus=0.0)

        # RLS update using latest measurement and past lags
        self._update_rls(y_curr)

        u_correction = self._solve_mpc(y_curr)
        if u_correction is None:
            u_correction = 0.0

        # If below target, do not add insulin
        if current_glucose < self.target:
            u_correction = min(u_correction, 0.0)

        self._shift_histories(y_curr, u_correction)

        basal_out = max(0.0, self.basal_rate + u_correction)
        return Action(basal=basal_out, bolus=0.0)

    def _shift_histories(self, y_new: float, u_new: float) -> None:
        self.prev_y2 = self.prev_y1
        self.prev_y1 = y_new
        self.prev_u2 = self.prev_u1
        self.prev_u1 = u_new

    def reset(self) -> None:
        self.theta = np.array([0.9, -0.05, -0.8, -0.2], dtype=float)
        self.P = np.eye(4) * 500.0
        self.prev_y1 = 0.0
        self.prev_y2 = 0.0
        self.prev_u1 = 0.0
        self.prev_u2 = 0.0
