"""
Safety-first PID demo for the simglucose environment.

Goals
- Target glucose: 140 mg/dL.
- Normal band: bias toward staying under 180 mg/dL, but prioritize avoiding
  hypoglycemia; it's acceptable to sit mildly above 180 for short periods to
  avoid dips.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from simglucose.actuator.pump import InsulinPump
from simglucose.controller.base import Action, Controller
from simglucose.patient.t1dpatient import T1DPatient
from simglucose.sensor.cgm import CGMSensor
from simglucose.simulation.env import T1DSimEnv
from simglucose.simulation.scenario_gen import RandomScenario
from simglucose.simulation.sim_engine import SimObj

LOG = logging.getLogger(__name__)
# PATIENT_PARAMS = Path(__file__).resolve().parent / "simglucose" / "params" / "vpatient_params.csv"
# Modified to point to a relative path or handle missing file gracefully if needed
# For now, we assume the environment has access to simglucose params or we mock it.
# In the original file it was relative to __file__.
# We will try to keep it working if simglucose is installed.
import simglucose

PATIENT_PARAMS = Path(simglucose.__file__).parent / "params" / "vpatient_params.csv"


class SafetyFirstPID(Controller):
    """
    PID tuned to avoid hypoglycemia:
    - Only doses when BG is above target.
    - Aggressively backs off near a low guard.
    - Keeps a small basal trickle but trims it during lows.
    """

    def __init__(
        self,
        target: float = 140.0,
        hypo_guard: float = 95.0,
        soft_upper: float = 180.0,
        kp: float = 0.012,
        ki: float = 0.00004,
        kd: float = 0.01,
        basal_floor: float = 0.35,
        max_u_per_min: float = 14.0,
    ):
        self.target = target
        self.hypo_guard = hypo_guard
        self.soft_upper = soft_upper
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.basal_floor = basal_floor  # fraction of steady-state basal always on
        self.max_u_per_min = max_u_per_min

        self._integral = 0.0
        self._prev_bg = None
        self._basal_ss = None
        self._params_cache = None

    def _steady_basal(self, patient_name: str) -> float:
        # Steady-state basal from patient parameters (U/min)
        if self._params_cache is None:
            if PATIENT_PARAMS.exists():
                self._params_cache = pd.read_csv(PATIENT_PARAMS).set_index("Name")
            else:
                # Fallback if file not found
                return 0.015  # Default fallback

        if self._params_cache is not None and patient_name in self._params_cache.index:
            row = self._params_cache.loc[patient_name]
            return float(row["u2ss"] * row["BW"] / 6000.0)
        return 0.015  # Default fallback

    def reset(self):
        self._integral = 0.0
        self._prev_bg = None
        self._basal_ss = None

    def policy(self, observation, reward, done, **kwargs):
        sample_time = kwargs.get("sample_time", 5.0)
        patient_name = kwargs.get("patient_name", "adolescent#001")

        if self._basal_ss is None:
            self._basal_ss = self._steady_basal(patient_name)

        bg = float(observation.CGM)

        # Hypo guard: if below guard, strip dosing to a small floor and reset I-term.
        if bg < self.hypo_guard:
            self._integral = 0.0
            basal = (self._basal_ss or 0.0) * self.basal_floor
            self._prev_bg = bg
            return Action(basal=basal, bolus=0.0)

        # Only integrate error when above target to bias against lows.
        over_target = max(bg - self.target, 0.0)
        self._integral = min(self._integral + over_target * sample_time, 600.0)

        derivative = 0.0
        if self._prev_bg is not None:
            derivative = max((bg - self._prev_bg) / sample_time, 0.0)
        self._prev_bg = bg

        control = (
            self.kp * over_target + self.ki * self._integral + self.kd * derivative
        )

        # Soften dosing when close to target to reduce oscillations.
        if bg < self.soft_upper:
            band = self.soft_upper - self.target
            scale = (bg - self.target) / band if band > 0 else 0.0
            control *= max(scale, 0.0)

        basal_floor_u = (self._basal_ss or 0.0) * self.basal_floor
        basal = basal_floor_u + control
        basal = float(np.clip(basal, 0.0, self.max_u_per_min))
        return Action(basal=basal, bolus=0.0)
