# filepath: f:\1_YX\CGM\111\simglucose\controller\pid_tuner.py
"""
使用PSO离线/在线整定PID (P, I, D) 参数。
- 目标函数基于在simglucose环境中运行短时仿真，最小化ITAE等指标，并强化低血糖惩罚与控制抖动惩罚。
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
from datetime import datetime

from .pid_ctrller import PIDController
from .pso_utils import pso_optimize

# 延迟导入以避免顶层依赖问题
try:
    from simglucose.simulation.env import T1DSimEnv
    from simglucose.patient.t1dpatient import T1DPatient
    from simglucose.sensor.cgm import CGMSensor
    from simglucose.actuator.pump import InsulinPump
    from simglucose.simulation.scenario import CustomScenario
    from simglucose.simulation.sim_engine import SimObj, sim  # 单实例仿真
except Exception:
    T1DSimEnv = None  # type: ignore


@dataclass
class TuningConfig:
    duration_hours: float = 6.0
    start_hour: int = 6
    seed: int = 123
    patient_name: str = "adult#001"
    sensor_name: str = "Dexcom"
    pump_name: str = "Insulet"
    target_glucose: float = 140.0
    # 三餐之一，短时整定建议选择一餐窗口
    meals: Optional[List[Tuple[float, float]]] = None  # [(time_hour, carbs_g)]

    # 控制模式：'P'、'PI'、'PD'、'PID'
    mode: str = "PID"

    # PSO参数
    particle_num: int = 24
    max_iter: int = 20
    kp_bounds: Tuple[float, float] = (0.0, 10.0)
    ki_bounds: Tuple[float, float] = (0.0, 0.05)
    kd_bounds: Tuple[float, float] = (0.0, 100.0)

    # 可选：与正式仿真保持一致的 PID 运行参数
    pid_kwargs: Optional[Dict] = None

    # 目标权重（可通过外部覆盖）
    w_itae: float = 1.0
    w_iae: float = 0.02
    w_hypo: float = 5.0
    w_hyper: float = 0.2
    w_du2: float = 5.0
    w_total_insulin: float = 0.0  # 对总胰岛素的软约束（U）
    w_tir: float = 0.0  # 对(1-TIR)的惩罚，默认关闭
    # 新增：稳态偏差惩罚（末尾窗口均值绝对误差）
    w_ss_bias: float = 0.5
    ss_window_min: float = 30.0


# 评估一个PID参数在短时窗口内的性能（返回越小越好）
def evaluate_pid(P: float, I: float, D: float, cfg: TuningConfig) -> float:
    assert T1DSimEnv is not None, "simglucose is required"

    # 根据模式修正参数与运行期开关
    mode = (cfg.mode or "PID").upper()
    if mode == "P":
        I_eff, D_eff = 0.0, 0.0
        integral_enabled = False
    elif mode == "PD":
        I_eff, D_eff = 0.0, D
        integral_enabled = False
    elif mode == "PI":
        I_eff, D_eff = I, 0.0
        integral_enabled = True
    else:  # PID
        I_eff, D_eff = I, D
        integral_enabled = True

    # 构建环境
    patient = T1DPatient.withName(cfg.patient_name)
    sensor = CGMSensor.withName(cfg.sensor_name, seed=cfg.seed)
    pump = InsulinPump.withName(cfg.pump_name)
    meals = cfg.meals or [(7.0, 45)]
    start_time = datetime.now().replace(
        hour=cfg.start_hour, minute=0, second=0, microsecond=0
    )
    scenario = CustomScenario(start_time=start_time, scenario=meals)
    env = T1DSimEnv(patient, sensor, pump, scenario)

    # 与正式仿真一致的 PID 结构（含限幅/滤波/死区等）
    pid_defaults = dict(
        u_min=0.0,
        u_max=0.12,
        d_alpha=0.3,
        deadband=5.0,
        i_leak=0.01,
        i_limit=4000,
        slew_rate=0.01,
        integral_enabled=integral_enabled,
    )
    if cfg.pid_kwargs:
        pid_defaults.update(cfg.pid_kwargs)
        # 以模式为准强制覆盖
        pid_defaults["integral_enabled"] = integral_enabled

    ctrl = PIDController(
        P=P, I=I_eff, D=D_eff, target=cfg.target_glucose, **pid_defaults
    )

    # 单次仿真
    duration_min = int(cfg.duration_hours * 60)
    sample_time = 5  # min

    # 状态累计
    iae = 0.0
    itae = 0.0
    hypo_pen = 0.0
    hyper_pen = 0.0
    du2 = 0.0
    prev_u = 0.0
    in_range_min = 0.0
    total_min = 0.0
    total_insulin_u = 0.0
    # 新增：记录BG序列用于稳态偏差
    _bg_series: List[float] = []

    # 环境步进
    obs_step = env.reset()
    try:
        obs, reward, done, info = obs_step  # 兼容Step命名元组
    except Exception:
        # 回退：若无法解包，则按属性访问
        obs = getattr(obs_step, "observation", obs_step)
        done = getattr(obs_step, "done", False)
    tmin = 0.0
    while not done and tmin < duration_min:
        action = ctrl.policy(obs, reward=0, done=False, sample_time=sample_time)
        obs, reward, done, info = env.step(action)

        bg = float(getattr(obs, "CGM", getattr(obs, "BG", 0.0)))
        _bg_series.append(bg)
        err = abs(bg - cfg.target_glucose)
        iae += err * sample_time
        itae += err * tmin  # ITAE（min 加权）

        # 强化低血糖惩罚，适度高血糖惩罚
        if bg < 70:
            hypo_pen += (70.0 - bg) ** 2 * sample_time  # mg^2/dL^2 * min
        if bg > 180:
            hyper_pen += (bg - 180.0) * sample_time

        # 控制抖动惩罚
        u = float(getattr(action, "basal", 0.0))
        du2 += (u - prev_u) ** 2
        prev_u = u

        # TIR 与总胰岛素
        if 70.0 <= bg <= 180.0:
            in_range_min += sample_time
        total_min += sample_time
        total_insulin_u += u * sample_time  # U/min * min = U

        tmin += sample_time

    tir = 1.0 - ((total_min - in_range_min) / total_min) if total_min > 0 else 0.0

    # 新增：末尾窗口的稳态偏差（均值绝对误差）
    ss_bias = 0.0
    if _bg_series:
        n_win = max(1, int(getattr(cfg, "ss_window_min", 30.0) / sample_time))
        last_vals = _bg_series[-n_win:]
        ss_bias = float(np.mean([abs(b - cfg.target_glucose) for b in last_vals]))

    # 组合目标
    cost = (
        cfg.w_itae * itae
        + cfg.w_iae * iae
        + cfg.w_hypo * hypo_pen
        + cfg.w_hyper * hyper_pen
        + cfg.w_du2 * du2
        + cfg.w_total_insulin * total_insulin_u
        + cfg.w_tir * (1.0 - tir)
        + getattr(cfg, "w_ss_bias", 0.0) * ss_bias
    )
    return float(cost)


def pso_tune_pid(
    cfg: TuningConfig, warm_start: Optional[Tuple[float, float, float]] = None
):
    mode = (cfg.mode or "PID").upper()

    # 构建按模式的边界与到(P,I,D)的映射
    if mode == "P":
        bounds = [cfg.kp_bounds]

        def to_pid(x):
            return float(x[0]), 0.0, 0.0

        x0 = None if warm_start is None else np.asarray([warm_start[0]], dtype=float)
    elif mode == "PD":
        bounds = [cfg.kp_bounds, cfg.kd_bounds]

        def to_pid(x):
            return float(x[0]), 0.0, float(x[1])

        x0 = (
            None
            if warm_start is None
            else np.asarray([warm_start[0], warm_start[2]], dtype=float)
        )
    elif mode == "PI":
        bounds = [cfg.kp_bounds, cfg.ki_bounds]

        def to_pid(x):
            return float(x[0]), float(x[1]), 0.0

        x0 = (
            None
            if warm_start is None
            else np.asarray([warm_start[0], warm_start[1]], dtype=float)
        )
    else:  # PID
        bounds = [cfg.kp_bounds, cfg.ki_bounds, cfg.kd_bounds]

        def to_pid(x):
            return float(x[0]), float(x[1]), float(x[2])

        x0 = None if warm_start is None else np.asarray(warm_start, dtype=float)

    def obj(x: np.ndarray) -> float:
        P, I, D = to_pid(x)
        return evaluate_pid(P, I, D, cfg)

    res = pso_optimize(
        obj,
        bounds,
        particle_num=cfg.particle_num,
        max_iter=cfg.max_iter,
        seed=cfg.seed,
        x_init_best=x0,
    )

    # 当前最优解
    P, I, D = to_pid(res.x_best)
    # 参数轨迹（按模式映射回三元组）
    param_history = [tuple(to_pid(x)) for x in getattr(res, "x_history", [])]

    return {
        "P": float(P),
        "I": float(I),
        "D": float(D),
        "cost": float(res.f_best),
        "history": res.history,
        "param_history": [
            (float(p), float(i), float(d)) for (p, i, d) in param_history
        ],
    }
