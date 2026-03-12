# filepath: f:\1_YX\CGM\Sim_patient\simglucose\controller\pso_pid_ctrller.py
from .base import Controller, Action
import numpy as np
import os
import sys
from collections import deque
import logging
import pandas as pd
import pkg_resources

logger = logging.getLogger(__name__)


class _SimplePID:
    """轻量PID，输出单位默认按 U/h，调用方可自行换算为 U/min"""

    def __init__(
        self, kp, ki, kd, target=112.0, dt_minutes=5.0, out_min=0.0, out_max_h=None
    ):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.target = target
        self.dt_h = max(dt_minutes, 1e-6) / 60.0
        self.out_min = out_min
        self.out_max_h = out_max_h
        self.integral = 0.0
        self.prev_err = 0.0

    def reset(self):
        self.integral = 0.0
        self.prev_err = 0.0

    def compute(self, predicted_glucose):
        err = float(predicted_glucose - self.target)
        self.integral += err * self.dt_h
        deriv = (err - self.prev_err) / self.dt_h if self.dt_h > 0 else 0.0
        u_h = self.kp * err + self.ki * self.integral + self.kd * deriv
        self.prev_err = err
        # 限幅（U/h）
        if self.out_max_h is not None:
            u_h = float(np.clip(u_h, self.out_min, self.out_max_h))
        else:
            u_h = max(u_h, self.out_min)
        return u_h


def _default_pso_config(pd_root):
    # jj.txt里的参数范围
    return {
        "particle_num": 50,
        "max_iter": 30,
        "kp_bounds": [0.5, 2.5],
        "ki_bounds": [0.0001, 0.007],
        "kd_bounds": [350, 750],
        "opt_every_n": 3,
        "target_glucose": 112,
    }


def _try_import_pd_components():
    """尝试从兄弟目录 PD 引入组件；失败时返回降级占位"""
    # 目录：Sim_patient/simglucose/controller -> 回到CGM根目录
    current_dir = os.path.dirname(__file__)
    cgm_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    pd_root = os.path.join(cgm_root, "PD")
    if os.path.isdir(pd_root) and pd_root not in sys.path:
        sys.path.append(pd_root)
        src_dir = os.path.join(pd_root, "src")
        if os.path.isdir(src_dir) and src_dir not in sys.path:
            sys.path.append(src_dir)

    PD = {
        "has_torch": False,
        "CNNTransformer": None,
        "optimize_pid": None,
        "mock_simulate_forward": None,
        "pso_config": _default_pso_config(pd_root),
        "model_path": os.path.join(pd_root, "models", "cnn_transformer.pth"),
        "pd_root": pd_root,
    }

    # 读取pso.yaml
    try:
        import yaml  # type: ignore

        cfg_path = os.path.join(pd_root, "config", "pso.yaml")
        if os.path.isfile(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                PD["pso_config"].update(yaml.safe_load(f) or {})
    except Exception as e:
        logger.warning(f"加载 PD pso.yaml 失败，使用默认配置：{e}")

    # 导入模型类
    try:
        import torch  # noqa: F401

        PD["has_torch"] = True
        try:
            from src.predictor.model import CNNTransformer  # type: ignore

            PD["CNNTransformer"] = CNNTransformer
        except Exception as e:
            logger.warning(f"导入 CNNTransformer 失败：{e}")
    except Exception:
        PD["has_torch"] = False

    # 导入PSO与前向仿真
    try:
        from src.controller.pso import optimize_pid  # type: ignore

        PD["optimize_pid"] = optimize_pid
    except Exception as e:
        logger.warning(f"导入 optimize_pid 失败，将使用简化PSO：{e}")

    try:
        from src.simulator.simulator import mock_simulate_forward  # type: ignore

        PD["mock_simulate_forward"] = mock_simulate_forward
    except Exception:
        PD["mock_simulate_forward"] = None

    return PD


def _fallback_mock_forward(state, insulin_u_h, carbs=0.0, dt_h=5 / 60):
    # 非生理的玩具模型，只用于PSO目标函数近似
    glucose = state.get("glucose", 120.0)
    sensitivity = 0.1
    carb_impact = 10.0
    decay = 0.05
    insulin_effect = -sensitivity * insulin_u_h * dt_h
    carb_effect = carb_impact * carbs * dt_h
    new_glucose = (
        glucose + insulin_effect + carb_effect - decay * (glucose - 112) * dt_h
    )
    return {"glucose": max(new_glucose, 40)}


class PsoPidController(Controller):
    """
    基于 jj.txt 的 预测 + PSO 调参 PID 闭环控制器
    - 输入：每5分钟采样的 (CGM, CHO, insulin) 共24步序列
    - 预测：CNN+Transformer 预测30min血糖（若不可用则退化为当前CGM）
    - PSO：以 ITAE 目标优化 (Kp,Ki,Kd)，默认每 opt_every_n 步优化一次
    - PID：输出胰岛素速率（U/min），限幅
    """

    def __init__(
        self,
        target=112.0,
        max_basal_u_min=0.10,  # 约6 U/h
        use_predictor=True,
        use_pso=True,
        dt_minutes=5.0,
    ):
        # 不使用基类 init_state
        self.target = target
        self.dt_minutes = dt_minutes
        self.max_basal_u_min = max_basal_u_min  # 若无法估计基线时的硬上限
        self.use_predictor = use_predictor
        self.use_pso = use_pso

        # 历史缓存
        self.hist_glucose = deque(maxlen=24)
        self.hist_carbs = deque(maxlen=24)
        self.hist_insulin = deque(maxlen=24)
        self.step_count = 0
        self.last_basal_u_min = 0.0
        self.baseline_basal_u_min = None  # 患者个体基线基础率 (U/min)
        self.dynamic_max_basal_u_min = None  # 基于个体的动态上限

        # 引入PD组件
        self.PD = _try_import_pd_components()
        self.opt_every_n = int(self.PD["pso_config"].get("opt_every_n", 3))

        # 载入预测模型（若可用）
        self._model = None
        if (
            self.use_predictor
            and self.PD["has_torch"]
            and self.PD["CNNTransformer"] is not None
        ):
            try:
                import torch

                self._model = self.PD["CNNTransformer"]()
                model_path = self.PD["model_path"]
                if os.path.isfile(model_path):
                    state = torch.load(model_path, map_location="cpu")
                    # 兼容直接保存的state_dict或整模型
                    if isinstance(state, dict) and any(
                        k.startswith("cnn.") or k.startswith("fusion.")
                        for k in state.keys()
                    ):
                        self._model.load_state_dict(state)
                    else:
                        self._model = state
                self._model.eval()
                self._torch = torch
                logger.info("PSO-PID 预测模型已加载")
            except Exception as e:
                logger.warning(f"加载预测模型失败，退化为自回归：{e}")
                self._model = None
        else:
            if self.use_predictor:
                logger.warning("未启用或无法加载预测模型，退化为使用当前CGM作为预测")

        # 初始 PID 参数（若PSO不可用则使用该值）
        self.kp, self.ki, self.kd = 1.0, 0.001, 500.0
        self._pid = _SimplePID(
            self.kp,
            self.ki,
            self.kd,
            target=self.target,
            dt_minutes=self.dt_minutes,
            out_min=0.0,
            out_max_h=None,  # 这里返回的是增量（U/h），不单独限幅，统一在合成总基础率后限幅
        )

    def __deepcopy__(self, memo):
        """避免递归复制到模块/函数对象导致的pickle错误，返回一个等价的新实例。"""
        return PsoPidController(
            target=self.target,
            max_basal_u_min=self.max_basal_u_min,
            use_predictor=self.use_predictor,
            use_pso=self.use_pso,
            dt_minutes=self.dt_minutes,
        )

    def _estimate_baseline_basal(self, patient_name: str) -> float:
        """按simglucose的Basal-Bolus同式估计基线基础率：u2ss*BW/6000 (U/min)。"""
        try:
            PATIENT_PARA_FILE = pkg_resources.resource_filename(
                "simglucose", "params/vpatient_params.csv"
            )
            params = pd.read_csv(PATIENT_PARA_FILE)
            sel = params[params.Name.str.match(patient_name)]
            if sel.empty:
                # 使用平均值
                u2ss = 1.43
                BW = 57.0
            else:
                u2ss = sel.u2ss.values.item()
                BW = sel.BW.values.item()
            basal = float(u2ss * BW / 6000.0)  # U/min
            return max(basal, 0.0)
        except Exception as e:
            logger.warning(
                f"估计基线基础率失败，使用默认上限 {self.max_basal_u_min}：{e}"
            )
            return 0.0

    def _predict_next_glucose(self):
        # 历史不足则返回最近CGM
        if len(self.hist_glucose) < 24:
            return self.hist_glucose[-1] if self.hist_glucose else 120.0

        if self._model is None:
            return float(self.hist_glucose[-1])

        try:
            x_np = np.stack(
                [
                    np.array(self.hist_glucose, dtype=np.float32),
                    np.array(self.hist_carbs, dtype=np.float32),
                    np.array(self.hist_insulin, dtype=np.float32),
                ],
                axis=-1,
            )  # [24,3]
            x_np = x_np[None, ...]  # [1,24,3]
            with self._torch.no_grad():
                x = self._torch.from_numpy(x_np)
                y = self._model(x)  # [1]
                return float(y.reshape(-1)[0].item())
        except Exception as e:
            logger.warning(f"预测失败，使用当前CGM，原因：{e}")
            return float(self.hist_glucose[-1])

    def _pso_optimize(self, predicted_glucose):
        if not self.use_pso:
            return self.kp, self.ki, self.kd

        # 优先使用 PD 的 optimize_pid
        if self.PD.get("optimize_pid") is not None:
            try:
                kp, ki, kd = self.PD["optimize_pid"](
                    predicted_glucose, self.PD["pso_config"], target=self.target
                )
                return float(kp), float(ki), float(kd)
            except Exception as e:
                logger.warning(f"调用 PD optimize_pid 失败，改用简化PSO：{e}")

        # 简化 PSO（无pyswarm时）：网格粗搜索
        cfg = self.PD["pso_config"]
        kb = cfg
        kp_range = np.linspace(kb["kp_bounds"][0], kb["kp_bounds"][1], 5)
        ki_range = np.linspace(kb["ki_bounds"][0], kb["ki_bounds"][1], 5)
        kd_range = np.linspace(kb["kd_bounds"][0], kb["kd_bounds"][1], 5)
        best = (self.kp, self.ki, self.kd)
        best_cost = float("inf")
        # 前向仿真
        fwd = self.PD.get("mock_simulate_forward") or _fallback_mock_forward
        for kp in kp_range:
            for ki in ki_range:
                for kd in kd_range:
                    pid = _SimplePID(
                        kp,
                        ki,
                        kd,
                        target=self.target,
                        dt_minutes=self.dt_minutes,
                        out_min=0.0,
                        out_max_h=self.max_basal_u_min * 60,
                    )
                    # 模拟6步（30min）
                    t_grid = np.arange(0, 6) * (self.dt_minutes)
                    state = {"glucose": predicted_glucose}
                    errs = []
                    for _ in range(6):
                        u_h = pid.compute(state["glucose"])  # U/h
                        state = fwd(state, u_h, carbs=0.0, dt_h=self.dt_minutes / 60.0)
                        errs.append(abs(state["glucose"] - self.target))
                    errs = np.asarray(errs, dtype=float)
                    # ITAE 积分（近似）
                    itae = np.trapz(t_grid * errs, t_grid)
                    if itae < best_cost:
                        best_cost = itae
                        best = (kp, ki, kd)
        return tuple(map(float, best))

    def policy(self, observation, reward, done, **info):
        # 提取输入
        sample_time = float(info.get("sample_time", self.dt_minutes))
        self.dt_minutes = sample_time
        meal_cho = float(info.get("meal", 0.0))  # g/min（环境返回的是每分钟平均）
        cgm = float(getattr(observation, "CGM", 0.0))

        # 首步根据患者估计基线基础率，并设置动态上限
        if self.baseline_basal_u_min is None:
            pname = info.get("patient_name", "Average")
            self.baseline_basal_u_min = self._estimate_baseline_basal(pname)
            # 动态上限：基线的4倍，且不低于硬上限（两者取最大）
            self.dynamic_max_basal_u_min = max(
                self.max_basal_u_min, self.baseline_basal_u_min * 4.0
            )

        # 更新历史（将上一步指令作为当前步的insulin特征）
        self.hist_glucose.append(cgm)
        self.hist_carbs.append(meal_cho)
        self.hist_insulin.append(
            self.last_basal_u_min
        )  # 使用“实际执行”的基础率（U/min）

        self.step_count += 1

        # 预测未来30min血糖
        pred_glucose = self._predict_next_glucose()

        # 周期性PSO调参
        if (self.step_count == 1) or (self.step_count % max(self.opt_every_n, 1) == 0):
            kp, ki, kd = self._pso_optimize(pred_glucose)
            self.kp, self.ki, self.kd = kp, ki, kd
            self._pid = _SimplePID(
                self.kp,
                self.ki,
                self.kd,
                target=self.target,
                dt_minutes=self.dt_minutes,
                out_min=0.0,
                out_max_h=None,
            )
            logger.info(f"PSO更新PID: kp={kp:.4f}, ki={ki:.6f}, kd={kd:.2f}")

        # 计算PID增量（U/h -> U/min），叠加到基线基础率上
        u_delta_h = self._pid.compute(pred_glucose)
        u_delta_min = u_delta_h / 60.0
        basal_u_min = self.baseline_basal_u_min + u_delta_min
        # 统一限幅到个体化动态上限
        max_lim = self.dynamic_max_basal_u_min or self.max_basal_u_min
        basal_u_min = float(np.clip(basal_u_min, 0.0, max_lim))
        self.last_basal_u_min = basal_u_min

        return Action(basal=basal_u_min, bolus=0.0)

    def reset(self):
        self.hist_glucose.clear()
        self.hist_carbs.clear()
        self.hist_insulin.clear()
        self.step_count = 0
        self.last_basal_u_min = 0.0
        self.baseline_basal_u_min = None
        self.dynamic_max_basal_u_min = None
        if hasattr(self, "_pid") and self._pid is not None:
            self._pid.reset()
