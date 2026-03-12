import logging

import numpy as np
import pandas as pd
import pkg_resources
import scipy.optimize as optimize

from .base import Action
from .base import Controller

logger = logging.getLogger(__name__)

CONTROL_QUEST = pkg_resources.resource_filename("simglucose", "params/Quest.csv")
PATIENT_PARA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/vpatient_params.csv"
)

DEFAULT_ARX_ORDER = 5
DEFAULT_ARX_THETA = np.array(
    [
        1.61751481,
        -0.57688853,
        -0.03658752,
        -0.00371150,
        -0.01030075,
        0.02391641,
        0.04874458,
        0.02592481,
        0.00339690,
        -0.02226433,
        0.08209373,
        0.08957301,
        0.09020363,
        0.07151224,
        0.05873284,
        1.52397835,
    ],
    dtype=float,
)


class SimpleMPCController(Controller):
    """
    A minimal MPC-style controller using an ARX(5) prediction model.
    """

    def __init__(
        self,
        target=140.0,
        prediction_horizon=2.0,
        control_horizon=1.0,
        arx_order=5,
        rls_lambda=0.98,
        rls_delta=1000.0,
        max_basal_multiplier=5.0,
        du_penalty=0.1,
        hypo_penalty=20.0,
    ):
        self.quest = pd.read_csv(CONTROL_QUEST)
        self.patient_params = pd.read_csv(PATIENT_PARA_FILE)
        self.target = float(target)
        self.prediction_horizon = float(prediction_horizon)
        self.control_horizon = float(control_horizon)
        self.arx_order = int(arx_order)
        self.rls_lambda = float(rls_lambda)
        self.rls_delta = float(rls_delta)
        self.max_basal_multiplier = float(max_basal_multiplier)
        self.du_penalty = float(du_penalty)
        self.hypo_penalty = float(hypo_penalty)
        self.reset()

    def policy(self, observation, reward, done, **kwargs):
        sample_time = float(kwargs.get("sample_time", 1.0))
        pname = kwargs.get("patient_name", "")
        meal = float(kwargs.get("meal", 0.0))

        current_glucose = float(observation.CGM)
        patient = self._lookup_patient(pname)
        basal = patient["basal"]

        pred_steps = max(1, int(round(self.prediction_horizon * 60.0 / sample_time)))
        ctrl_steps = max(1, int(round(self.control_horizon * 60.0 / sample_time)))

        meal_pred = np.zeros(pred_steps, dtype=float)
        if meal > 0:
            meal_duration = max(1, int(round(30.0 / sample_time)))
            meal_pred[: min(meal_duration, pred_steps)] = meal

        max_basal = max(self.max_basal_multiplier * basal, basal)
        u0 = np.full(ctrl_steps, basal, dtype=float)

        if self._can_update_arx():
            phi = self._build_phi(
                self.glucose_history, self.insulin_history, self.meal_history
            )
            self._rls_update(phi, current_glucose)

        self.glucose_history.append(current_glucose)

        result = optimize.minimize(
            self._objective,
            u0,
            args=(
                basal,
                meal_pred,
                pred_steps,
                self.glucose_history,
                self.insulin_history,
                self.meal_history,
            ),
            bounds=[(0.0, max_basal)] * ctrl_steps,
            method="L-BFGS-B",
        )

        if result.success and result.x.size > 0:
            optimal_rate = float(result.x[0])
        else:
            logger.warning("MPC solve failed; using basal rate.")
            optimal_rate = basal

        self.insulin_history.append(optimal_rate)
        self.meal_history.append(meal)

        return Action(basal=optimal_rate, bolus=0)

    def _objective(
        self,
        u,
        basal,
        meal_pred,
        pred_steps,
        g_hist,
        u_hist,
        m_hist,
    ):
        g_pred = self._predict_glucose(
            g_hist, u_hist, m_hist, u, meal_pred, pred_steps, basal
        )
        err = g_pred[1:] - self.target
        cost = np.sum(err**2)
        du = np.diff(np.concatenate(([u[0]], u)))
        cost += self.du_penalty * np.sum(du**2)
        cost += self.hypo_penalty * np.sum(np.maximum(0.0, 70.0 - g_pred[1:]) ** 2)
        return float(cost)

    def _predict_glucose(
        self,
        g_hist,
        u_hist,
        m_hist,
        u_future,
        meal_future,
        pred_steps,
        basal,
    ):
        g_hist = self._pad_history(
            g_hist, g_hist[-1] if g_hist else self.target, self.arx_order
        )
        u_hist = self._pad_history(
            u_hist, u_hist[-1] if u_hist else basal, self.arx_order
        )
        m_hist = self._pad_history(m_hist, 0.0, self.arx_order)

        g_queue = list(g_hist)
        u_queue = list(u_hist)
        m_queue = list(m_hist)
        g = np.zeros(pred_steps + 1, dtype=float)
        g[0] = float(g_queue[-1])
        for k in range(pred_steps):
            u_k = float(u_future[k] if k < len(u_future) else u_future[-1])
            meal_k = float(meal_future[k] if k < len(meal_future) else 0.0)

            u_queue.append(u_k)
            if len(u_queue) > self.arx_order:
                u_queue.pop(0)
            m_queue.append(meal_k)
            if len(m_queue) > self.arx_order:
                m_queue.pop(0)

            phi = self._build_phi(g_queue, u_queue, m_queue)
            g_next = float(np.dot(self.theta, phi))
            g[k + 1] = max(g_next, 40.0)

            g_queue.append(g[k + 1])
            if len(g_queue) > self.arx_order:
                g_queue.pop(0)
        return g

    def _can_update_arx(self):
        return (
            len(self.glucose_history) >= self.arx_order
            and len(self.insulin_history) >= self.arx_order
            and len(self.meal_history) >= self.arx_order
        )

    def _build_phi(self, g_hist, u_hist, m_hist):
        g = list(g_hist)[-self.arx_order :]
        u = list(u_hist)[-self.arx_order :]
        m = list(m_hist)[-self.arx_order :]
        return np.array(
            list(reversed(g)) + list(reversed(u)) + list(reversed(m)) + [1.0],
            dtype=float,
        )

    def _pad_history(self, history, fill_value, length):
        history = list(history)
        if len(history) >= length:
            return history[-length:]
        return [fill_value] * (length - len(history)) + history

    def _rls_update(self, phi, y):
        phi = phi.reshape(-1, 1)
        denom = self.rls_lambda + float(phi.T @ self.P @ phi)
        if denom <= 1e-12:
            return
        k_gain = (self.P @ phi) / denom
        y_hat = float(phi.T @ self.theta)
        err = float(y) - y_hat
        self.theta = self.theta + k_gain.flatten() * err
        self.P = (self.P - k_gain @ phi.T @ self.P) / self.rls_lambda
        self.P = 0.5 * (self.P + self.P.T)

    def _lookup_patient(self, name):
        if name and any(self.quest.Name.str.match(name)):
            quest = self.quest[self.quest.Name.str.match(name)]
            params = self.patient_params[self.patient_params.Name.str.match(name)]
            cr = float(quest.CR.values.item())
            cf = float(quest.CF.values.item())
            u2ss = float(params.u2ss.values.item())
            bw = float(params.BW.values.item())
        else:
            cr = 15.0
            cf = 50.0
            u2ss = 1.43
            bw = 57.0
        basal = u2ss * bw / 6000.0
        return {"cr": cr, "cf": cf, "basal": basal}

    def reset(self):
        self.glucose_history = []
        self.insulin_history = []
        self.meal_history = []
        theta_size = 3 * self.arx_order + 1
        self.theta = np.zeros(theta_size, dtype=float)
        if self.arx_order == DEFAULT_ARX_ORDER:
            self.theta[:] = DEFAULT_ARX_THETA
        else:
            self.theta[0] = 1.0
        self.P = np.eye(theta_size, dtype=float) * self.rls_delta
