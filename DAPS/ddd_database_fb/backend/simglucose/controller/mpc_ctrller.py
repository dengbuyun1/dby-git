# filepath: f:\1_YX\CGM\111\simglucose\controller\mpc_ctrller.py
from .base import Controller
from .base import Action
import numpy as np
import logging
import pandas as pd
import pkg_resources

logger = logging.getLogger(__name__)
PATIENT_PARA_FILE = pkg_resources.resource_filename(
    "simglucose", "params/vpatient_params.csv"
)


class MPCController(Controller):
    """
    轻量级MPC控制器（ARX + 栅格首控优化）。
    重要说明：horizon 按“分钟”理解，内部会按 sample_time(分钟/步) 自动换算为预测步数。
    采用 offset-free 机制（常值扰动估计）消除稳态偏差。
    """

    def __init__(
        self,
        target: float = 120.0,  # 目标血糖 mg/dL
        horizon: int = 60,  # 预测时域（分钟）; 例：GuardianRT=5min，则60->12步
        u_min: float = 0.0,  # U/min
        u_max: float = 2.0,  # U/min（环境里会再次裁剪到[0,14]）
        slew_rate: float = 0.05,  # 每步最大变化量 U/min（按控制调用周期）
        Qy: float = 1.0,  # 状态（血糖）偏差权重
        Ru: float = 1e-3,  # 胰岛素用量权重（相对基线），不再乘以horizon
        Rdu: float = 0.1,  # 本步相对上步的变化惩罚
        ridge: float = 1e-3,  # 在线最小二乘的岭回归系数
        use_cgm: bool = True,  # True: 用CGM做建模/控制；False: 若有BG则用BG
        grid_size: int = 9,  # 候选u的离散点数
        offset_gain: float = 0.2,  # offset-free扰动估计的步进增益(0..1)
        offset_clip: float = 50.0,  # 偏置限幅，避免数值飘逸
    ):
        self.target = float(target)
        self.horizon_min = int(max(1, horizon))  # 以“分钟”为单位保存
        self.u_min = float(u_min)
        self.u_max = float(u_max)
        self.slew_rate = float(max(0.0, slew_rate))
        self.Qy = float(max(1e-9, Qy))
        self.Ru = float(max(0.0, Ru))
        self.Rdu = float(max(0.0, Rdu))
        self.ridge = float(max(0.0, ridge))
        self.use_cgm = bool(use_cgm)
        self.grid_size = int(max(3, grid_size))
        self.offset_gain = float(np.clip(offset_gain, 0.0, 1.0))
        self.offset_clip = float(max(1.0, offset_clip))

        # 在线辨识的数据缓存与参数（ARX: G_{k+1} = a*G_k + b*u_k + c*meal_k + d + w_hat）
        self._X_hist = []  # 每行: [G_k, u_k, meal_k, 1]
        self._y_hist = []  # G_{k+1}
        self._theta = np.array([0.99, -0.2, 0.3, 0.0], dtype=float)  # a,b,c,d 的初值
        self._offset_hat = 0.0  # 常值扰动估计（offset-free）

        # 运行时状态
        self._last_u = None
        self._last_G = None
        self._last_meal = 0.0
        self._basal_est = 0.05  # 缺省基线（U/min，约3U/h）

    def _horizon_steps(self, sample_time: float) -> int:
        # 将分钟换算为离散步数
        return int(max(1, round(self.horizon_min / max(1e-6, sample_time))))

    def _estimate_basal_from_patient(self, patient_name: str | None):
        try:
            if patient_name is None:
                raise ValueError("no patient name")
            params = pd.read_csv(PATIENT_PARA_FILE)
            row = params[params.Name == patient_name]
            if len(row) == 1:
                u2ss = float(row.u2ss.values.item())
                BW = float(row.BW.values.item())
            else:
                # 平均值
                u2ss = 1.43
                BW = 57.0
        except Exception:
            u2ss = 1.43
            BW = 57.0
        self._basal_est = u2ss * BW / 6000.0  # U/min
        self._basal_est = float(np.clip(self._basal_est, self.u_min, self.u_max))

    def _current_bg(self, observation):
        if (
            not self.use_cgm
            and hasattr(observation, "BG")
            and observation.BG is not None
        ):
            return float(observation.BG)
        return float(observation.CGM)

    def _update_arx(self, G_prev: float, u_prev: float, meal_prev: float, G_now: float):
        x = np.array([G_prev, u_prev, meal_prev, 1.0], dtype=float)
        self._X_hist.append(x)
        self._y_hist.append(float(G_now))
        if len(self._X_hist) >= 5:
            X = np.vstack(self._X_hist)
            y = np.array(self._y_hist)
            lamI = self.ridge * np.eye(X.shape[1])
            try:
                theta = np.linalg.solve(X.T @ X + lamI, X.T @ y)
            except np.linalg.LinAlgError:
                theta, *_ = np.linalg.lstsq(X, y, rcond=None)
            a, b, c, d = theta
            a = float(np.clip(a, 0.5, 1.2))
            b = float(np.clip(b, -5.0, 0.0))  # 胰岛素应降低血糖
            c = float(np.clip(c, 0.0, 5.0))  # 进餐提高血糖
            d = float(np.clip(d, -20.0, 20.0))
            self._theta = np.array([a, b, c, d], dtype=float)

    def _one_step_predict(self, G: float, u: float, meal: float) -> float:
        a, b, c, d = self._theta
        return a * G + b * u + c * meal + d + self._offset_hat

    def _predict_traj(self, G0: float, u: float, meal: float, steps: int):
        a, b, c, d = self._theta
        G = float(G0)
        traj = []
        for _ in range(steps):
            G = a * G + b * u + c * meal + d + self._offset_hat
            traj.append(G)
        return np.array(traj, dtype=float)

    def _candidate_controls(self):
        # 生成受限的候选u（首个动作），考虑爬坡与边界
        if self._last_u is None:
            lo = max(self.u_min, self._basal_est - self.slew_rate)
            hi = min(self.u_max, self._basal_est + self.slew_rate)
        else:
            lo = max(self.u_min, self._last_u - self.slew_rate)
            hi = min(self.u_max, self._last_u + self.slew_rate)
        if hi < lo:
            lo, hi = hi, lo
        grid = np.linspace(lo, hi, num=self.grid_size)
        grid = np.unique(
            np.clip(
                np.hstack([grid, [self._basal_est, self.u_min, self.u_max]]),
                self.u_min,
                self.u_max,
            )
        )
        return grid

    def policy(self, observation, reward, done, **kwargs):
        sample_time = float(kwargs.get("sample_time", 5.0))
        steps = self._horizon_steps(sample_time)
        pname = kwargs.get("patient_name", None)
        meal = float(kwargs.get("meal", 0.0))  # g/min（环境传入的平均值）

        # 初次获取basal估计
        if self._last_u is None:
            self._estimate_basal_from_patient(pname)
            self._last_u = self._basal_est

        G_now = self._current_bg(observation)

        # 用上一时刻样本更新ARX，并基于一步预测误差更新offset（offset-free）
        if self._last_G is not None:
            self._update_arx(self._last_G, self._last_u, self._last_meal, G_now)
            # 一步预测误差作为扰动修正
            y_pred = self._one_step_predict(self._last_G, self._last_u, self._last_meal)
            err = float(G_now - y_pred)
            self._offset_hat += self.offset_gain * err
            self._offset_hat = float(
                np.clip(self._offset_hat, -self.offset_clip, self.offset_clip)
            )

        # 候选u搜索，基于ARX模型预测未来轨迹
        best_u = self._last_u
        best_cost = float("inf")
        for u in self._candidate_controls():
            traj = self._predict_traj(G_now, u, meal, steps)
            err = traj - self.target
            cost = (
                self.Qy * float(err @ err)
                + self.Ru * (u - self._basal_est) ** 2
                + self.Rdu * (u - self._last_u) ** 2
            )
            if cost < best_cost:
                best_cost = cost
                best_u = float(u)

        # 应用边界与爬坡（再次保证）
        du = float(np.clip(best_u - self._last_u, -self.slew_rate, self.slew_rate))
        u_cmd = float(np.clip(self._last_u + du, self.u_min, self.u_max))

        logger.info(
            f"MPC: G={G_now:.1f}, target={self.target:.1f}, meal={meal:.2f} g/min, "
            f"step={steps}, u*={best_u:.3f}, cmd={u_cmd:.3f}, basal~{self._basal_est:.3f}, "
            f"off={self._offset_hat:.2f}"
        )

        # 更新内部状态以便下步辨识
        self._last_G = G_now
        self._last_meal = meal
        self._last_u = u_cmd

        # 输出：全部作为basal通道（bolus置0，环境会把两者相加成总速率）
        return Action(basal=u_cmd, bolus=0.0)

    def reset(self):
        self._X_hist = []
        self._y_hist = []
        self._theta = np.array([0.99, -0.2, 0.3, 0.0], dtype=float)
        self._offset_hat = 0.0
        self._last_u = None
        self._last_G = None
        self._last_meal = 0.0
        self._basal_est = 0.05
