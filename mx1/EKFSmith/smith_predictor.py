"""
smith_predictor.py
==================
Smith Predictor 用于补偿胰岛素注射→血糖响应的纯时间延迟。

解决的问题：
  - 皮下胰岛素注射后约 30-60 min 才对血糖产生完整效果
  - TCP 通信 + 电机执行存在几秒到几十秒的附加延迟
  - 如果控制器不知道这个延迟，会导致过度补偿（震荡/低血糖危险）

Smith Predictor 原理：
  ┌──────────────────────────────────────────────────────┐
  │                  Smith Predictor 结构                 │
  │                                                       │
  │  r(k) →[ Controller ]→ u(k)→[ 真实系统 P(z)·z^{-d} ]→ y(k)
  │              ↑                     ↓                  │
  │              │         [ 内部模型  P_m(z) ]→ ŷ_m      │
  │              │         [ 延迟模型  z^{-d}  ]→ ŷ_d     │
  │              │                                        │
  │              └──── e = r - ŷ_d - (y - ŷ_d) ─────────┘
  │                         └── 等效：e = r - y + (ŷ_m - ŷ_d)
  └──────────────────────────────────────────────────────┘

  效果：消除反馈环中的延迟，控制器看到的是"无延迟"系统，
        从而可以设计更激进（响应更快）的控制律而不震荡。

内部模型（离散时间一阶血糖响应模型）：
  G_m(k+1) = a·G_m(k) + b·u(k)
  其中 a = exp(-dt/τ_g)，b 为稳态增益换算

可与任意控制器（PID / MPC）串联使用。
"""

from __future__ import annotations

from collections import deque

import numpy as np


# ─── Smith Predictor ─────────────────────────────────────────────────────────

class SmithPredictor:
    """
    离散时间 Smith Predictor，用于补偿胰岛素→血糖的时间延迟。

    用法（与 PID/MPC 控制器配合）：
        sp = SmithPredictor(delay_steps=6, dt=5.0)
        sp.initialize(G0=130.0)

        for each control step:
            # 1. 获取原始测量（CGM 或 EKF 估计值）
            y_measured = cgm_or_ekf_G

            # 2. Smith 补偿：得到等效"无延迟"误差信号
            e_smith = sp.compute_error(reference=120.0, y_measured=y_measured)

            # 3. 将 e_smith 送入控制器
            u = pid.compute(e_smith)

            # 4. 更新内部模型（用本步控制量）
            sp.update_model(u)
    """

    def __init__(
        self,
        delay_steps: int = 6,
        dt: float = 5.0,
        tau_g: float = 40.0,
        Kg: float = -0.5,
        Gb: float = 120.0,
    ):
        """
        Args:
            delay_steps: 延迟步数 d（steps）。
                         d = delay_min / dt
                         例：30 min 延迟 / 5 min步长 = 6 步
            dt:  采样间隔（分钟）
            tau_g: 血糖-胰岛素响应时间常数（分钟），描述内部模型速度
                   典型值：30~60 min
            Kg:  稳态增益 (mg/dL)/(U/hr)，负值（胰岛素降血糖）
                 典型值：-0.3 ~ -1.0
            Gb:  基础血糖（用于内部模型初始化）
        """
        self.d = int(delay_steps)
        self.dt = float(dt)
        self.Gb = float(Gb)

        # 一阶离散模型参数
        # G_m(k+1) = alpha·G_m(k) + beta·u(k)
        self.alpha = float(np.exp(-dt / tau_g))
        # beta = Kg·(1 - alpha) 保证稳态增益为 Kg（U/hr → mg/dL）
        self.beta = float(Kg * (1.0 - self.alpha))

        # 延迟缓冲区（存放过去 d 步的控制量）
        self._u_buffer: deque[float] = deque([0.0] * self.d, maxlen=self.d)

        # 内部模型状态：无延迟预测 ŷ_m 和有延迟预测 ŷ_d
        self._G_m: float = Gb    # 无延迟模型血糖状态
        self._G_d: float = Gb    # 有延迟模型血糖状态（另一个并行模型）

        # 额外延迟缓冲区（用于 G_d）
        self._Gm_buffer: deque[float] = deque([Gb] * self.d, maxlen=self.d)

    # ── 初始化 ────────────────────────────────────────────────────────────────

    def initialize(self, G0: float = 120.0, u_basal: float = 0.0) -> None:
        """
        初始化内部状态，以当前血糖和基础胰岛素速率为稳态。

        Args:
            G0: 当前血糖估计 (mg/dL)
            u_basal: 基础胰岛素速率 (U/hr)
        """
        self._G_m = G0
        self._G_d = G0
        self._u_buffer = deque([u_basal] * self.d, maxlen=self.d)
        self._Gm_buffer = deque([G0] * self.d, maxlen=self.d)
        self.Gb = G0

    # ── 内部模型更新 ──────────────────────────────────────────────────────────

    def update_model(self, u_U_per_hr: float) -> None:
        """
        用本步控制量 u 推进内部模型一步。

        必须在 compute_error() 之后、下一步 compute_error() 之前调用。

        Args:
            u_U_per_hr: 本步胰岛素注射速率 (U/hr)
        """
        # 推进无延迟模型
        G_m_new = self.alpha * self._G_m + self.beta * u_U_per_hr
        self._Gm_buffer.append(G_m_new)

        # 推进有延迟模型（用 d 步前的控制量）
        u_delayed = self._u_buffer[0]   # 最老的控制量（d 步前）
        G_d_new = self.alpha * self._G_d + self.beta * u_delayed

        # 更新状态
        self._G_m = G_m_new
        self._G_d = G_d_new

        # 将本步 u 加入延迟缓冲区
        self._u_buffer.append(u_U_per_hr)

    # ── 计算 Smith 补偿后的误差信号 ───────────────────────────────────────────

    def compute_error(self, reference: float, y_measured: float) -> float:
        """
        计算 Smith Predictor 补偿后的等效误差（送给控制器）。

        Smith 误差公式：
            e_smith = r - y - (ŷ_d - ŷ_m)
                    = r - y + (ŷ_m - ŷ_d)

        当内部模型精确时，(ŷ_m - ŷ_d) 正好抵消真实系统的延迟影响，
        控制器看到的等效闭环中没有延迟。

        Args:
            reference: 目标血糖 (mg/dL)，通常 120 mg/dL
            y_measured: 当前血糖测量值（CGM 或 EKF 估计 G）

        Returns:
            e_smith: Smith 补偿后的误差 (mg/dL)
        """
        # Smith 补偿量：无延迟预测 - 有延迟预测
        smith_compensation = self._G_m - self._G_d

        # 等效"无延迟"误差
        e = reference - y_measured + smith_compensation
        return float(e)

    # ── 仅获取预测（不更新）──────────────────────────────────────────────────

    @property
    def predicted_G_no_delay(self) -> float:
        """内部模型预测的无延迟血糖（mg/dL）"""
        return float(self._G_m)

    @property
    def predicted_G_with_delay(self) -> float:
        """内部模型预测的有延迟血糖（mg/dL）"""
        return float(self._G_d)

    @property
    def smith_compensation(self) -> float:
        """当前 Smith 补偿量（mg/dL）"""
        return float(self._G_m - self._G_d)

    def get_status(self) -> dict:
        """返回内部状态（用于调试和日志）"""
        return {
            "G_m": self.predicted_G_no_delay,
            "G_d": self.predicted_G_with_delay,
            "smith_comp": self.smith_compensation,
            "delay_steps": self.d,
            "alpha": self.alpha,
            "beta": self.beta,
        }

    # ── 参数自适应（可选）────────────────────────────────────────────────────

    def adapt_model(
        self,
        y_measured: float,
        learning_rate: float = 0.05,
    ) -> None:
        """
        简单的在线模型适应：用测量-预测误差修正内部模型状态。
        （可选使用，使 Smith Predictor 对模型失配更鲁棒）

        Args:
            y_measured: 当前真实测量
            learning_rate: 学习率（0 ~ 0.2 为合理范围）
        """
        error = y_measured - self._G_d
        self._G_m += learning_rate * error
        self._G_d += learning_rate * error


# ─── 针对 DAPS 硬件延迟的专用封装 ────────────────────────────────────────────

class DAPSDelayCompensator:
    """
    DAPS 系统的综合延迟补偿器，处理两类延迟：

    1. 生理延迟（皮下胰岛素→血糖，~30-60 min）→ Smith Predictor
    2. 硬件延迟（TCP + 电机执行，~几秒到1步）→ 延迟缓冲区预补偿

    典型用法：
        compensator = DAPSDelayCompensator()
        compensator.initialize(G0=130.0)

        for each 5-min step:
            # EKF 估计血糖
            G_est = ekf.G_est

            # Smith 补偿
            e_compensated = compensator.compute_error(target=120, G_measured=G_est)

            # PID/MPC 基于补偿误差计算控制量
            u = controller.compute(e_compensated)

            # 更新补偿器内部模型
            compensator.update(u)
    """

    def __init__(
        self,
        dt: float = 5.0,
        insulin_delay_min: float = 30.0,
        hw_delay_steps: int = 1,
        tau_g: float = 45.0,
        Kg: float = -0.4,
    ):
        """
        Args:
            dt: 采样间隔（分钟）
            insulin_delay_min: 胰岛素生理延迟（分钟），默认 30 min
            hw_delay_steps: 硬件/TCP 延迟（步数），默认 1 步（5 min）
            tau_g: 血糖响应时间常数（分钟）
            Kg: 胰岛素-血糖稳态增益 (mg/dL)/(U/hr)
        """
        total_delay_steps = int(round(insulin_delay_min / dt)) + hw_delay_steps

        self.smith = SmithPredictor(
            delay_steps=total_delay_steps,
            dt=dt,
            tau_g=tau_g,
            Kg=Kg,
        )
        self.total_delay_min = total_delay_steps * dt
        self.hw_delay_steps = hw_delay_steps

    def initialize(self, G0: float = 120.0, u_basal: float = 0.0) -> None:
        self.smith.initialize(G0=G0, u_basal=u_basal)

    def compute_error(self, target: float, G_measured: float) -> float:
        return self.smith.compute_error(reference=target, y_measured=G_measured)

    def update(self, u_U_per_hr: float) -> None:
        self.smith.update_model(u_U_per_hr)

    def adapt(self, G_measured: float, learning_rate: float = 0.05) -> None:
        """可选：在线适应内部模型"""
        self.smith.adapt_model(G_measured, learning_rate)

    def get_status(self) -> dict:
        s = self.smith.get_status()
        s["total_delay_min"] = self.total_delay_min
        return s
