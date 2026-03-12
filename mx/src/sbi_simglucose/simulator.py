from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
import types
from typing import Iterable, Sequence

import numpy as np


DEFAULT_PARAMETER_KEYS = ("kabs", "kp1", "kp2", "kp3")


@dataclass
class SimulatorConfig:
    patient_name: str = "adolescent#001"
    sensor_name: str = "GuardianRT"
    pump_name: str = "Insulet"
    sim_minutes: int = 1440
    seed: int = 7
    # (minute_from_start, grams)
    meal_schedule: tuple[tuple[int, float], ...] = ((30, 45.0), (300, 70.0), (720, 80.0))
    parameter_keys: tuple[str, ...] = DEFAULT_PARAMETER_KEYS


class SimglucoseSBISimulator:
    """Parameterized simglucose simulator for SBI data generation.

    Theta is interpreted as multiplicative scales on selected patient parameters.
    Example with DEFAULT_PARAMETER_KEYS:
        theta = [s_kabs, s_kp1, s_kp2, s_kp3]
    where each s_* multiplies the patient's nominal parameter value.
    """

    def __init__(self, config: SimulatorConfig):
        self.config = config

    @staticmethod
    def _install_gym_stub_if_missing() -> None:
        # Local simglucose package imports gym registration in __init__.
        if "gym" in sys.modules:
            return
        gym_mod = types.ModuleType("gym")
        envs_mod = types.ModuleType("gym.envs")
        reg_mod = types.ModuleType("gym.envs.registration")

        def register(*_args, **_kwargs):
            return None

        reg_mod.register = register
        envs_mod.registration = reg_mod
        gym_mod.envs = envs_mod

        sys.modules["gym"] = gym_mod
        sys.modules["gym.envs"] = envs_mod
        sys.modules["gym.envs.registration"] = reg_mod

    @staticmethod
    def _parse_step_output(step_obj):
        # simglucose simulation.env returns a namedtuple Step(observation, reward, done, info)
        if hasattr(step_obj, "observation") and hasattr(step_obj, "done"):
            obs = step_obj.observation
            done = bool(step_obj.done)
            info = step_obj.info if isinstance(step_obj.info, dict) else {}
            return obs, done, info

        if isinstance(step_obj, tuple) and len(step_obj) >= 4:
            obs, _reward, done, info = step_obj[:4]
            return obs, bool(done), info if isinstance(info, dict) else {}

        raise TypeError(f"Unsupported simglucose step output type: {type(step_obj)}")

    @staticmethod
    def _extract_cgm(obs) -> float:
        if hasattr(obs, "CGM"):
            return float(obs.CGM)
        if isinstance(obs, dict) and "CGM" in obs:
            return float(obs["CGM"])
        return float(obs)

    def _build_env(self, seed: int):
        self._install_gym_stub_if_missing()

        from simglucose.actuator.pump import InsulinPump
        from simglucose.controller.base import Action
        from simglucose.patient.t1dpatient import T1DPatient
        from simglucose.sensor.cgm import CGMSensor
        from simglucose.simulation.env import T1DSimEnv
        from simglucose.simulation.scenario import CustomScenario

        patient = T1DPatient.withName(self.config.patient_name, seed=seed)
        sensor = CGMSensor.withName(self.config.sensor_name, seed=seed + 100)
        pump = InsulinPump.withName(self.config.pump_name)

        start_time = datetime(2025, 1, 1, 6, 0, 0)
        scenario_data = [
            (timedelta(minutes=int(m)), float(g)) for m, g in self.config.meal_schedule
        ]
        scenario = CustomScenario(start_time=start_time, scenario=scenario_data)

        env = T1DSimEnv(patient=patient, sensor=sensor, pump=pump, scenario=scenario)

        nominal = {k: float(patient._params[k]) for k in self.config.parameter_keys}
        basal_u_per_min = float(patient._params.u2ss * patient._params.BW / 6000.0)

        return env, patient, Action, nominal, basal_u_per_min

    def simulate(self, theta_scales: Sequence[float], seed: int | None = None) -> np.ndarray:
        if len(theta_scales) != len(self.config.parameter_keys):
            raise ValueError(
                f"theta length {len(theta_scales)} != number of parameter_keys {len(self.config.parameter_keys)}"
            )

        sim_seed = self.config.seed if seed is None else int(seed)
        env, patient, Action, nominal, basal_u_per_min = self._build_env(seed=sim_seed)

        # Apply scaled parameters to this virtual patient.
        for key, scale in zip(self.config.parameter_keys, theta_scales):
            patient._params[key] = max(1e-8, nominal[key] * float(scale))

        # Reset after parameter injection.
        first = env.reset()
        obs0, done, _ = self._parse_step_output(first)
        cgm_values = [self._extract_cgm(obs0)]

        n_steps = max(1, int(self.config.sim_minutes / env.sample_time))
        action = Action(basal=basal_u_per_min, bolus=0.0)

        for _ in range(n_steps - 1):
            if done:
                break
            raw = env.step(action)
            obs, done, _ = self._parse_step_output(raw)
            cgm_values.append(self._extract_cgm(obs))

        # Keep fixed observation length.
        if len(cgm_values) < n_steps:
            cgm_values.extend([cgm_values[-1]] * (n_steps - len(cgm_values)))

        x = np.asarray(cgm_values[:n_steps], dtype=np.float32)
        x = np.clip(x, 40.0, 400.0)
        return x

    def batch_simulate(self, thetas: Iterable[Sequence[float]], seed_offset: int = 0) -> np.ndarray:
        xs = []
        for i, theta in enumerate(thetas):
            xs.append(self.simulate(theta_scales=theta, seed=self.config.seed + seed_offset + i))
        return np.stack(xs, axis=0)
