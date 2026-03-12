"""
ekf_glucose.py
==============
基于 Bergman Minimal Model（简化双室模型）的扩展卡尔曼滤波器（EKF）

解决的问题：
  1. CGM 传感器噪声（±10~20 mg/dL）
  2. CGM 相对真实血糖的 ~10-15 min 间质液延迟
  3. 系统隐藏状态估计（IOB、远端胰岛素效应 X）

状态向量（4维）：
  x[0] = G   : 血浆血糖浓度 (mg/dL)
  x[1] = X   : 远端(效应室)胰岛素浓度 (1/min)，与 G 相乘产生葡萄糖利用
  x[2] = I1  : 皮下快室胰岛素 (mU/L)，u → I1
  x[3] = I2  : 皮下慢室胰岛素 (mU/L)，I1 → I2 → 血浆

观测量：
  y = CGM ≈ G + 传感器噪声

控制输入：
  u = 胰岛素注射速率 (U/hr)
"""

from __future__ import annotations

import numpy as np


# ─── 默认生理参数（Bergman+双室皮下模型，基于文献典型值）────────────────────

DEFAULT_PARAMS = {
    # Bergman minimal model
    "p1": 0.028,        # 胰岛素无关的葡萄糖清除率 (1/min)
    "p2": 0.028,        # 效应室胰岛素消失率 (1/min)
    "p3": 5.0e-5,       # 效应室胰岛素敏感性 (1/min per mU/L)
    "Gb": 120.0,        # 基础血糖 (mg/dL)
    "Ib": 10.0,         # 基础血浆胰岛素 (mU/L)
    "BW": 70.0,         # 体重 (kg)，用于 U → mU/L 换算
    "VG": 1.49,         # 葡萄糖分布容积 (dL/kg)，用于 CHO→血糖换算
    # 双室皮下模型
    "ka1": 0.006,       # I1 → blood 速率 (1/min)
    "ka2": 0.06,        # I2 → blood 速率 (1/min)（在 Bergman 语境中约等于 kd）
    "ksc": 0.066,       # 皮下吸收速率 I1→I2 (1/min)
}

# 过程噪声协方差（可调，越大越信模型外的扰动/进餐）
DEFAULT_Q_DIAG = [5.0, 1e-6, 0.01, 0.01]   # [G, X, I1, I2]
DEFAULT_R = 25.0                             # CGM 测量噪声方差 (mg/dL)²，≈ ±5 mg/dL


class GlucoseEKF:
    """
    葡萄糖-胰岛素系统的扩展卡尔曼滤波器。

    用法：
        ekf = GlucoseEKF(dt=5.0)
        ekf.initialize(G0=130.0)
        for each 5-min step:
            ekf.predict(u_insulin=0.02)          # 预测
            x_est, P = ekf.update(cgm_reading)   # 更新
            G_estimated = x_est[0]
    """

    def __init__(
        self,
        dt: float = 5.0,
        params: dict | None = None,
        Q_diag: list[float] | None = None,
        R: float = DEFAULT_R,
        cho_disturbance_scale: float = 0.5,
    ):
        """
        Args:
            dt: 采样时间间隔（分钟），与仿真步长一致
            params: 生理参数字典（见 DEFAULT_PARAMS）
            Q_diag: 过程噪声协方差对角元素（4维）
            R: 测量噪声方差 (mg/dL)²
            cho_disturbance_scale: 进餐时对过程噪声 Q[G] 的放大倍数（处理进餐不确定性）
        """
        self.dt = float(dt)
        self.p = {**DEFAULT_PARAMS, **(params or {})}
        self.Q_diag = np.array(Q_diag or DEFAULT_Q_DIAG, dtype=np.float64)
        self.R = float(R)
        self.cho_scale = float(cho_disturbance_scale)

        # 状态维度
        self.n = 4

        # 滤波器状态（初始化后赋值）
        self.x: np.ndarray | None = None   # (4,) 状态估计
        self.P: np.ndarray | None = None   # (4,4) 协方差矩阵
        self._cho_buffer: float = 0.0       # 未消化碳水（用于进餐扰动建模）

    # ── 初始化 ──────────────────────────────────────────────────────────────

    def initialize(
        self,
        G0: float = 120.0,
        X0: float = 0.0,
        I1_0: float = 5.0,
        I2_0: float = 5.0,
        P0_diag: list[float] | None = None,
    ) -> None:
        """
        设置初始状态估计和协方差。

        Args:
            G0: 初始血糖估计 (mg/dL)
            X0: 初始效应室胰岛素（通常为0）
            I1_0, I2_0: 初始皮下胰岛素（稳态时约等于基础率/ka）
            P0_diag: 初始协方差对角元素（None 则自动设置）
        """
        self.x = np.array([G0, X0, I1_0, I2_0], dtype=np.float64)
        p0 = P0_diag or [200.0, 1e-4, 0.5, 0.5]
        self.P = np.diag(p0).astype(np.float64)

    # ── 非线性状态方程（连续时间，欧拉离散化）──────────────────────────────

    def _f(self, x: np.ndarray, u_mU_per_min: float, cho_g: float) -> np.ndarray:
        """
        状态方程 dx/dt（Bergman minimal model + 双室皮下模型）

        Args:
            x: 当前状态 [G, X, I1, I2]
            u_mU_per_min: 胰岛素输注速率（mU/min）
            cho_g: 本步进餐碳水（g），转换为葡萄糖 Ra 扰动

        Returns:
            dx (4,)：状态导数
        """
        G, X, I1, I2 = x
        p = self.p

        # CHO → 葡萄糖出现速率（简化一阶动力学）
        Ra = cho_g * 1000.0 / (p["BW"] * p["VG"] * 180.0)  # mg/dL/min（粗略）

        dG  = -p["p1"] * (G - p["Gb"]) - X * G + Ra
        dX  = -p["p2"] * X + p["p3"] * (I2 - p["Ib"])
        dI1 = -p["ksc"] * I1 + u_mU_per_min / (p["BW"] * p["VG"])
        dI2 =  p["ksc"] * I1 - p["ka2"] * I2

        return np.array([dG, dX, dI1, dI2])

    # ── 雅可比矩阵（对状态 x 的偏导）─────────────────────────────────────

    def _jacobian_F(self, x: np.ndarray) -> np.ndarray:
        """
        状态方程对 x 的雅可比矩阵 F = ∂f/∂x（用于 EKF 线性化）
        """
        G, X, I1, I2 = x
        p = self.p
        dt = self.dt

        # 连续时间 Jacobian（近似线性化）
        Fc = np.array([
            [-p["p1"] - X,   -G,          0.0,               0.0           ],
            [ 0.0,           -p["p2"],     0.0,               p["p3"]       ],
            [ 0.0,            0.0,        -p["ksc"],          0.0           ],
            [ 0.0,            0.0,         p["ksc"],         -p["ka2"]      ],
        ])
        # 离散化（一阶近似）：Fd ≈ I + Fc·dt
        Fd = np.eye(self.n) + Fc * dt
        return Fd

    # ── EKF 预测步 ──────────────────────────────────────────────────────────

    def predict(
        self,
        u_U_per_hr: float = 0.0,
        cho_g: float = 0.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        EKF 预测步（时间更新）。

        Args:
            u_U_per_hr: 胰岛素速率（U/hr），来自控制器输出
            cho_g: 本步进餐量（g），用于 Ra 扰动建模

        Returns:
            x_pred (4,), P_pred (4,4)
        """
        assert self.x is not None, "请先调用 initialize()"

        # U/hr → mU/min
        u_mU_per_min = u_U_per_hr * 1000.0 / 60.0

        # ① 状态预测（欧拉积分）
        dx = self._f(self.x, u_mU_per_min, cho_g)
        x_pred = self.x + dx * self.dt

        # 保证血糖非负
        x_pred[0] = max(x_pred[0], 1.0)

        # ② 协方差预测：P = F·P·Fᵀ + Q
        F = self._jacobian_F(self.x)
        Q = np.diag(self.Q_diag.copy())
        if cho_g > 0:
            Q[0, 0] *= (1.0 + self.cho_scale * cho_g)   # 进餐时放大 G 的过程噪声

        P_pred = F @ self.P @ F.T + Q

        self.x = x_pred
        self.P = P_pred
        return self.x.copy(), self.P.copy()

    # ── EKF 更新步 ──────────────────────────────────────────────────────────

    def update(self, cgm_reading: float) -> tuple[np.ndarray, np.ndarray]:
        """
        EKF 测量更新步（用 CGM 观测修正预测）。

        观测模型：y = H·x + noise，H = [1, 0, 0, 0]（CGM ≈ G）

        Args:
            cgm_reading: CGM 原始读数（mg/dL）

        Returns:
            x_est (4,), P_est (4,4): 更新后的状态估计和协方差
        """
        assert self.x is not None, "请先调用 initialize()"

        # 观测矩阵 H = [1, 0, 0, 0]
        H = np.array([[1.0, 0.0, 0.0, 0.0]])
        R = np.array([[self.R]])

        # 创新（残差）
        y_pred = H @ self.x           # 预测测量值 = G_hat
        innov = cgm_reading - y_pred[0]

        # 卡尔曼增益：K = P·Hᵀ·(H·P·Hᵀ + R)⁻¹
        S = H @ self.P @ H.T + R
        K = self.P @ H.T / S[0, 0]   # (4, 1)

        # 状态更新
        self.x = self.x + K[:, 0] * innov

        # 协方差更新（Joseph 稳定形式）
        I_KH = np.eye(self.n) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R @ K.T

        return self.x.copy(), self.P.copy()

    # ── 便捷属性 ────────────────────────────────────────────────────────────

    @property
    def G_est(self) -> float:
        """血糖估计值（mg/dL）"""
        return float(self.x[0])

    @property
    def X_est(self) -> float:
        """效应室胰岛素浓度估计（IOB 代理）"""
        return float(self.x[1])

    @property
    def IOB_est(self) -> float:
        """体内活性胰岛素估计（简化：用皮下两室之和）"""
        return float(self.x[2] + self.x[3])

    def get_state_dict(self) -> dict:
        """返回当前状态字典（方便接入 DAPS 日志）"""
        return {
            "G_est": self.G_est,
            "X_est": self.X_est,
            "I1_est": float(self.x[2]),
            "I2_est": float(self.x[3]),
            "IOB_est": self.IOB_est,
            "P_G": float(self.P[0, 0]),   # G 估计方差（均方根 = sqrt(P[0,0]) mg/dL）
        }
