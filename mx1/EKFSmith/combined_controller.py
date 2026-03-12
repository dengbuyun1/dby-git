"""
combined_controller.py
======================
EKF + Smith Predictor 的联合控制器封装。

架构：
  CGM(k) → EKF → G_est(k) → Smith Predictor → e_smith(k) → 基础控制器 → u(k)
                                                                ↓
                                                          Smith.update(u)
                                                          EKF.predict(u)

可直接替换 DAPS 的 algorithm_module.py 中的 InsulinCalculator，
接口保持兼容：输入 (bg, cgm, cho, timestamp)，输出 {insulin, basal, bolus, iob}。
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

import numpy as np

from ekf_glucose import GlucoseEKF, DEFAULT_PARAMS
from smith_predictor import DAPSDelayCompensator


# ─── 基础控制器协议（接受任意实现了 compute 方法的控制器）────────────────────

class BaseControllerProtocol(Protocol):
    def compute(self, error: float, dt_min: float) -> float:
        """
        Args:
            error: 误差（参考 - 估计），mg/dL
            dt_min: 时间步长（分钟）
        Returns:
            u: 胰岛素速率（U/hr）
        """
        ...


# ─── 内置简单 PID 控制器（如果没有外部控制器）───────────────────────────────

class SimplePID:
    """简单离散 PID，用于测试和 demo。"""

    def __init__(self, kp: float = 0.01, ki: float = 0.002, kd: float = 0.0,
                 output_min: float = 0.0, output_max: float = 2.0):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.output_min = output_min
        self.output_max = output_max
        self._integral = 0.0
        self._prev_error = 0.0

    def compute(self, error: float, dt_min: float = 5.0) -> float:
        # 注意：血糖高→误差为负（target - G < 0）→需要更多胰岛素
        # 这里定义误差 = G - target（正误差 = 高血糖 → 正控制量）
        self._integral += error * dt_min
        # 积分抗饱和
        self._integral = np.clip(self._integral, -100.0, 100.0)
        d_term = (error - self._prev_error) / max(dt_min, 0.1)
        self._prev_error = error

        u = self.kp * error + self.ki * self._integral + self.kd * d_term
        return float(np.clip(u, self.output_min, self.output_max))

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0


# ─── 联合控制器：EKF + Smith + 任意基础控制器 ────────────────────────────────

class EKFSmithController:
    """
    EKF + Smith Predictor 联合控制器。

    将 EKF（状态估计）和 Smith Predictor（延迟补偿）
    叠加到任意基础控制器（PID/MPC）之上。

    与 DAPS 的 algorithm_module.InsulinCalculator 接口兼容。

    用法：
        ctrl = EKFSmithController(
            base_controller=SimplePID(kp=0.02),
            target_bg=120.0,
            patient_params={"p1": 0.028, "Gb": 110.0}
        )
        ctrl.initialize(G0=130.0)

        # 每个 5-min 步：
        result = ctrl.step(cgm=125.0, cho=0.0, u_prev=0.02)
    """

    def __init__(
        self,
        base_controller: BaseControllerProtocol | None = None,
        target_bg: float = 120.0,
        dt: float = 5.0,
        # EKF 参数
        patient_params: dict | None = None,
        Q_diag: list | None = None,
        R: float = 25.0,
        # Smith 参数
        insulin_delay_min: float = 30.0,
        hw_delay_steps: int = 1,
        tau_g: float = 45.0,
        Kg: float = -0.4,
        # 控制限制
        basal_rate: float = 0.015,   # U/min → U/hr = 0.015*60
        u_max: float = 2.0,          # 最大胰岛素速率 (U/hr)
        low_bg_threshold: float = 80.0,   # 低血糖保护阈值 (mg/dL)
        use_smith: bool = True,
        use_ekf: bool = True,
        use_adapt: bool = False,        # 是否用在线自适应修正 Smith 模型
    ):
        self.target_bg = target_bg
        self.dt = dt
        self.basal_rate_U_hr = basal_rate * 60.0  # U/min → U/hr
        self.u_max = u_max
        self.low_bg_threshold = low_bg_threshold
        self.use_smith = use_smith
        self.use_ekf = use_ekf
        self.use_adapt = use_adapt

        # 基础控制器（默认简单 PID）
        self.controller = base_controller or SimplePID(kp=0.02, ki=0.003)

        # EKF
        self.ekf = GlucoseEKF(
            dt=dt,
            params=patient_params,
            Q_diag=Q_diag,
            R=R,
        )

        # Smith Predictor
        self.smith_comp = DAPSDelayCompensator(
            dt=dt,
            insulin_delay_min=insulin_delay_min,
            hw_delay_steps=hw_delay_steps,
            tau_g=tau_g,
            Kg=Kg,
        )

        # 内部状态
        self._u_prev: float = self.basal_rate_U_hr
        self._iob: float = 0.0   # 简化 IOB 追踪

    # ── 初始化 ──────────────────────────────────────────────────────────────

    def initialize(self, G0: float = 120.0) -> None:
        """
        Args:
            G0: 初始血糖估计 (mg/dL)
        """
        self.ekf.initialize(G0=G0)
        self.smith_comp.initialize(G0=G0, u_basal=self.basal_rate_U_hr)
        self._u_prev = self.basal_rate_U_hr
        self._iob = 0.0

    # ── 单步计算 ─────────────────────────────────────────────────────────────

    def step(
        self,
        cgm: float,
        cho: float = 0.0,
        bg: float | None = None,
    ) -> dict:
        """
        执行一步控制计算。

        Args:
            cgm: CGM 读数 (mg/dL)
            cho: 本步进餐碳水量 (g)
            bg:  真实血糖（若有，用于比较；没有则用 EKF 估计代替）

        Returns:
            dict 包含：
                insulin   - 本步胰岛素注射总剂量（U，对应1步）
                basal     - 基础胰岛素速率（U/hr）
                bolus     - 餐时大剂量（U）
                iob       - 体内活性胰岛素估计（U）
                G_est     - EKF 估计血糖（mg/dL）
                G_cgm     - 原始 CGM 读数
                error_raw - 原始误差（目标 - CGM）
                error_smith - Smith 补偿后误差
                smith_comp  - Smith 补偿量
        """
        # ── Step 1: EKF 预测 ────────────────────────────────────────────────
        if self.use_ekf:
            self.ekf.predict(u_U_per_hr=self._u_prev, cho_g=cho)
            self.ekf.update(cgm_reading=cgm)
            G_est = self.ekf.G_est
        else:
            G_est = cgm   # 不用 EKF，直接用 CGM

        # ── Step 2: 低血糖保护 ─────────────────────────────────────────────
        if G_est < self.low_bg_threshold:
            u = 0.0
            e_smith = float(self.target_bg - G_est)
            smith_val = 0.0
        else:
            # ── Step 3: Smith Predictor 计算补偿误差 ────────────────────────
            # 误差定义为 G_est - target（正值 = 高血糖 = 需要更多胰岛素）
            if self.use_smith:
                e_smith = self.smith_comp.compute_error(
                    target=self.target_bg, G_measured=G_est
                )
                smith_val = self.smith_comp.smith.smith_compensation
                # Smith 误差：target - G_est + (Gm - Gd)
                # 高血糖时 e_smith < 0，对控制器来说需要取反
                error_for_ctrl = -e_smith          # 正值 = 高血糖
            else:
                error_for_ctrl = G_est - self.target_bg
                e_smith = float(self.target_bg - G_est)
                smith_val = 0.0

            # ── Step 4: 基础控制器计算 u ──────────────────────────────────
            u_ctrl = self.controller.compute(
                error=error_for_ctrl, dt_min=self.dt
            )
            u = float(np.clip(u_ctrl, 0.0, self.u_max))

        # ── Step 5: 分解为 basal + bolus ──────────────────────────────────
        basal_U_hr = min(u, self.basal_rate_U_hr)
        bolus_U_hr = max(0.0, u - self.basal_rate_U_hr)

        # 本步实际注射量（U）= 速率(U/hr) × 步长(hr)
        insulin_step_U = u * (self.dt / 60.0)
        bolus_U = bolus_U_hr * (self.dt / 60.0)

        # 简化 IOB（一阶衰减追踪）
        self._iob = self._iob * 0.9 + insulin_step_U

        # ── Step 6: 更新 Smith 内部模型 ───────────────────────────────────
        if self.use_smith:
            self.smith_comp.update(u)
            if self.use_adapt and G_est > 40:
                self.smith_comp.adapt(G_est, learning_rate=0.03)

        self._u_prev = u

        return {
            "insulin":      float(insulin_step_U),
            "basal":        float(basal_U_hr),
            "bolus":        float(bolus_U),
            "iob":          float(self._iob),
            "G_est":        float(G_est),
            "G_cgm":        float(cgm),
            "error_raw":    float(self.target_bg - cgm),
            "error_smith":  float(e_smith),
            "smith_comp":   float(smith_val),
            "P_G":          float(self.ekf.P[0, 0]) if self.use_ekf else 0.0,
        }

    # ── 兼容 DAPS algorithm_module.InsulinCalculator 接口 ───────────────────

    def calculate(
        self,
        bg: float,
        cgm: float,
        cho: float,
        timestamp: datetime | None = None,
    ) -> dict:
        """
        与 DAPS algorithm_module.InsulinCalculator.calculate() 接口兼容。
        """
        return self.step(cgm=cgm, cho=cho, bg=bg)
