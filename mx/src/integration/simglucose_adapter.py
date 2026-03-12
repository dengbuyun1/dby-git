from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import sys
import types
import numpy as np

from src.model import PhysiologyModel


@dataclass
class StepResult:
    cgm: float
    meal_effect: float
    done: bool
    info: dict


class MockSimglucoseEnv:
    """Fallback environment to keep EKF/Smith loop runnable without simglucose."""

    def __init__(self, dt_minutes: int = 5, seed: int = 7):
        self.dt_minutes = dt_minutes
        self.rng = np.random.default_rng(seed)
        self.model = PhysiologyModel(params=self._default_params(), dt_minutes=dt_minutes)
        self._step = 0
        self._x = np.array([145.0, 0.0, 18.0], dtype=float)

    @staticmethod
    def _default_params():
        from src.config import PhysiologyParams

        return PhysiologyParams()

    def reset(self) -> StepResult:
        self._step = 0
        self._x = np.array([145.0, 0.0, 18.0], dtype=float)
        cgm = float(self._x[0] + self.rng.normal(0.0, 8.0))
        return StepResult(cgm=cgm, meal_effect=0.0, done=False, info={"source": "mock"})

    def _meal_effect(self, k: int) -> float:
        period = 288  # 24h with 5-min steps
        kmod = k % period
        if 20 <= kmod <= 35:
            return 1.0
        if 85 <= kmod <= 105:
            return 0.8
        if 160 <= kmod <= 180:
            return 1.2
        return 0.0

    def step(self, insulin_u_per_hr: float) -> StepResult:
        meal = self._meal_effect(self._step)
        insulin_u_per_min = float(insulin_u_per_hr) / 60.0
        self._x = self.model.step(self._x, insulin_u_per_min=insulin_u_per_min, meal_effect=meal)

        cgm = float(self._x[0] + self.rng.normal(0.0, 8.0))
        self._step += 1
        done = self._step >= 288
        return StepResult(cgm=cgm, meal_effect=meal, done=done, info={"source": "mock"})


class SimglucoseAdapter:
    """Adapter that prefers real simglucose backend and falls back to mock.

    Public command unit is `U/hr`. It is converted internally to simglucose `Action` unit (`U/min`).
    """

    def __init__(
        self,
        dt_minutes: int = 5,
        seed: int = 7,
        patient_name: str = "adolescent#001",
        sensor_name: str = "GuardianRT",
        pump_name: str = "Insulet",
    ):
        self.dt_minutes = dt_minutes
        self.seed = seed
        self.patient_name = patient_name
        self.sensor_name = sensor_name
        self.pump_name = pump_name

        self._backend = None
        self._backend_name = "mock"
        self._action_cls = None
        self._sample_time_min = float(dt_minutes)
        self._fallback_reason = ""

        self._init_backend()

    @staticmethod
    def _install_gym_stub_if_missing() -> None:
        """Local simglucose __init__ requires gym.register; provide stub if gym is absent."""
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
    def _extract_cgm(obs) -> float:
        if isinstance(obs, dict):
            for k in ("CGM", "cgm", "glucose", "bg"):
                if k in obs:
                    return float(obs[k])
        for attr in ("CGM", "cgm", "glucose", "bg"):
            if hasattr(obs, attr):
                return float(getattr(obs, attr))
        return float(obs)

    @staticmethod
    def _extract_meal(info: dict) -> float:
        if not isinstance(info, dict):
            return 0.0
        # simglucose meal unit is grams over sample interval. Convert to a soft disturbance scalar.
        meal_g = float(info.get("meal", 0.0))
        return 0.02 * max(0.0, meal_g)

    @staticmethod
    def _parse_env_output(step_obj):
        """Support both namedtuple Step and tuple outputs."""
        if hasattr(step_obj, "observation") and hasattr(step_obj, "done"):
            obs = step_obj.observation
            reward = float(getattr(step_obj, "reward", 0.0))
            done = bool(getattr(step_obj, "done", False))
            info = getattr(step_obj, "info", {})
            if not isinstance(info, dict):
                info = dict(info) if info is not None else {}
            return obs, reward, done, info

        if isinstance(step_obj, tuple) and len(step_obj) == 4:
            return step_obj

        raise TypeError(f"Unsupported env output type: {type(step_obj)}")

    def _init_backend(self) -> None:
        try:
            self._install_gym_stub_if_missing()

            from simglucose.controller.base import Action
            from simglucose.simulation.env import T1DSimEnv
            from simglucose.patient.t1dpatient import T1DPatient
            from simglucose.sensor.cgm import CGMSensor
            from simglucose.actuator.pump import InsulinPump
            from simglucose.simulation.scenario_gen import RandomScenario

            patient = T1DPatient.withName(self.patient_name)
            sensor = CGMSensor.withName(self.sensor_name, seed=self.seed)
            pump = InsulinPump.withName(self.pump_name)
            scenario = RandomScenario(start_time=datetime.now(), seed=self.seed)

            env = T1DSimEnv(patient=patient, sensor=sensor, pump=pump, scenario=scenario)

            self._backend = env
            self._backend_name = "simglucose"
            self._action_cls = Action
            self._sample_time_min = float(sensor.sample_time)
        except Exception as e:
            self._backend = MockSimglucoseEnv(dt_minutes=self.dt_minutes, seed=self.seed)
            self._backend_name = "mock"
            self._fallback_reason = f"{type(e).__name__}: {e}"

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def sample_time_min(self) -> float:
        return self._sample_time_min

    @property
    def fallback_reason(self) -> str:
        return self._fallback_reason

    def reset(self) -> StepResult:
        if self._backend_name == "mock":
            return self._backend.reset()

        raw = self._backend.reset()
        obs, _reward, done, info = self._parse_env_output(raw)
        cgm = self._extract_cgm(obs)
        return StepResult(cgm=cgm, meal_effect=0.0, done=bool(done), info=info)

    def step(self, insulin_u_per_hr: float) -> StepResult:
        if self._backend_name == "mock":
            return self._backend.step(insulin_u_per_hr)

        basal_u_per_min = float(insulin_u_per_hr) / 60.0
        action = self._action_cls(basal=basal_u_per_min, bolus=0.0)
        raw = self._backend.step(action)
        obs, _reward, done, info = self._parse_env_output(raw)
        cgm = self._extract_cgm(obs)
        meal_effect = self._extract_meal(info)
        return StepResult(cgm=cgm, meal_effect=meal_effect, done=bool(done), info=info)
