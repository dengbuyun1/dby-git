from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
import types
from typing import Iterable, Sequence

import numpy as np


DEFAULT_PARAMETER_KEYS = ("kabs", "kp1", "kp2", "kp3", "Vmx", "kmax", "p2u", "ka2")


@dataclass
class SimulatorConfig:
    patient_name: str = "adolescent#001"
    sensor_name: str = "GuardianRT"
    pump_name: str = "Insulet"
    sim_minutes: int = 1440
    seed: int = 7
    # (minute_from_start, grams)
    meal_schedule: tuple[tuple[int, float], ...] = (
        (30, 45.0),
        (300, 70.0),
        (720, 80.0),
    )
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
        self._install_gym_stub_if_missing()

        # [Fix 2] Pre-load and cache parameters to avoid repetitive CSV parsing in withName()
        from simglucose.patient.t1dpatient import T1DPatient
        from simglucose.sensor.cgm import CGMSensor
        from simglucose.actuator.pump import InsulinPump

        self._patient_params = T1DPatient.withName(config.patient_name)._params.copy()
        self._sensor_params = CGMSensor.withName(config.sensor_name)._params.copy()
        self._pump_params = InsulinPump.withName(config.pump_name)._params.copy()

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

        # Directly instantiate using cached parameters (replaces .withName())
        patient = T1DPatient(self._patient_params.copy(), seed=seed)
        patient.name = self.config.patient_name

        sensor = CGMSensor(self._sensor_params.copy(), seed=seed + 100)
        pump = InsulinPump(self._pump_params.copy())

        start_time = datetime(2025, 1, 1, 6, 0, 0)
        scenario_data = [
            (timedelta(minutes=int(m)), float(g)) for m, g in self.config.meal_schedule
        ]
        scenario = CustomScenario(start_time=start_time, scenario=scenario_data)

        env = T1DSimEnv(patient=patient, sensor=sensor, pump=pump, scenario=scenario)

        nominal = {k: float(patient._params[k]) for k in self.config.parameter_keys}
        basal_u_per_min = float(patient._params.u2ss * patient._params.BW / 6000.0)

        return env, patient, Action, nominal, basal_u_per_min

    def simulate(
        self, theta_scales: Sequence[float], seed: int | None = None
    ) -> np.ndarray:
        if len(theta_scales) != len(self.config.parameter_keys):
            raise ValueError(
                f"theta length {len(theta_scales)} != number of parameter_keys {len(self.config.parameter_keys)}"
            )

        sim_seed = self.config.seed if seed is None else int(seed)
        env, patient, Action, nominal, basal_u_per_min = self._build_env(seed=sim_seed)

        # Apply scaled parameters to this virtual patient.
        for key, scale in zip(self.config.parameter_keys, theta_scales):
            patient._params[key] = max(1e-8, nominal[key] * float(scale))

        # [Fix: Steady State Burn-in]
        # The UVA/Padova model starts from a hardcoded steady-state in simglucose.
        # By changing the parameters, the initial state is no longer in equilibrium,
        # causing artificial transients. We run a numeric ODE burn-in to find the true
        # steady-state for the new parameters before starting the evaluation scenario.
        patient.t0 = 0
        patient.reset()

        # Burn-in for equivalent of 48 hours (2880 mins) to let BG stabilize
        from simglucose.patient.t1dpatient import Action as PatientAction

        prev_bg = patient.observation.Gsub
        for _ in range(2880):
            patient.step(PatientAction(CHO=0, insulin=basal_u_per_min))
            curr_bg = patient.observation.Gsub
            if abs(curr_bg - prev_bg) < 0.01:
                break
            prev_bg = curr_bg

        # Reject unphysiological steady states (e.g. fasting BG out of bounds)
        # Simglucose nominal patients are typically ~140 mg/dL.
        if patient.observation.Gsub < 70.0 or patient.observation.Gsub > 250.0:
            # Return an array of 40s to force RestrictionEstimator to reject it
            return (
                np.ones(max(1, int(self.config.sim_minutes / env.sample_time))) * 40.0
            )

        # Set the burned-in state as the new initial state for the scenario
        patient._init_state = patient.state.copy()

        # Reset after parameter injection and steady-state burn-in
        first = env.reset()
        obs0, done, _ = self._parse_step_output(first)
        cgm_values = [self._extract_cgm(obs0)]

        n_steps = max(1, int(self.config.sim_minutes / env.sample_time))

        # [Fix 3] Prepare bolus schedule based on meal events
        # ICR (Insulin-to-Carb Ratio): simple approximation e.g., 1U per 10g CHO
        # Bolus must be in U/min (rate), so divide total U by env.sample_time (minutes per step)
        icr = 10.0
        bolus_map = {}
        for m_curr, g_curr in self.config.meal_schedule:
            step_idx = int(m_curr / env.sample_time)
            bolus_map[step_idx] = (
                bolus_map.get(step_idx, 0.0) + (g_curr / icr) / env.sample_time
            )

        for i in range(n_steps - 1):
            if done:
                break

            # Inject meal bolus at the exact step the meal happens
            bolus_u = bolus_map.get(i, 0.0)
            action = Action(basal=basal_u_per_min, bolus=bolus_u)

            raw = env.step(action)
            obs, done, _ = self._parse_step_output(raw)
            cgm_values.append(self._extract_cgm(obs))

        # Keep fixed observation length.
        if len(cgm_values) < n_steps:
            cgm_values.extend([cgm_values[-1]] * (n_steps - len(cgm_values)))

        x = np.asarray(cgm_values[:n_steps], dtype=np.float32)
        # [Fix 1] Removed np.clip(x, 40.0, 400.0) so RestrictionEstimator can detect pathological trajectories
        return x

    def batch_simulate(
        self, thetas: Iterable[Sequence[float]], seed_offset: int = 0
    ) -> np.ndarray:
        xs = []
        for i, theta in enumerate(thetas):
            xs.append(
                self.simulate(
                    theta_scales=theta, seed=self.config.seed + seed_offset + i
                )
            )
        return np.stack(xs, axis=0)
