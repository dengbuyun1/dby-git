"""
PID控制器实现
"""

from typing import Dict, Optional
from datetime import datetime
from .base_controller import BaseController


class PidController(BaseController):
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = None

    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: datetime
    ) -> Dict[str, float]:
        # 严格使用 self.params 中的值，不设硬编码默认值
        # 如果参数不存在，说明上位机还没发过来，此时不应进行计算
        if not self.params:
            # print("[PID] Waiting for parameters...")
            return {
                "insulin": 0.0,
                "basal": 0.0,
                "bolus": 0.0,
                "iob": 0.0,
                "cob": cho,
            }

        try:
            # 直接从 params 获取，不使用任何业务逻辑默认值 (如 120.0)
            # get(key, 0) 仅用于防止 NoneType 转换错误，实际数值完全由 params 决定
            kp = float(self.params.get("kp", 0))
            ki = float(self.params.get("ki", 0))
            kd = float(self.params.get("kd", 0))

            # 获取目标血糖，优先使用 'target'
            if "target" in self.params:
                target_bg = float(self.params["target"])
            elif "target_bg" in self.params:
                target_bg = float(self.params["target_bg"])
            else:
                # 如果没有目标值，无法计算误差，直接返回 0
                print("[PID] Error: No target BG parameter received!")
                return {
                    "insulin": 0.0,
                    "basal": 0.0,
                    "bolus": 0.0,
                    "iob": 0.0,
                    "cob": cho,
                }

        except (ValueError, TypeError) as e:
            print(f"[PID] Parameter error: {e}")
            return {
                "insulin": 0.0,
                "basal": 0.0,
                "bolus": 0.0,
                "iob": 0.0,
                "cob": cho,
            }

        # 简单的PID实现
        # 使用 CGM (连续血糖监测值) 计算误差，而不是 BG (指尖血)
        error = cgm - target_bg

        dt = 0.0
        if self.last_time:
            dt = (timestamp - self.last_time).total_seconds() / 60.0  # 分钟

        if dt > 0:
            self.integral += error * dt
            derivative = (error - self.last_error) / dt
        else:
            derivative = 0.0

        # 防止积分饱和
        self.integral = max(min(self.integral, 100), -100)

        p_term = kp * error
        i_term = ki * self.integral
        d_term = kd * derivative
        output = p_term + i_term + d_term

        # 加上碳水前馈 (已移除，以确保纯PID控制)
        # carb_bolus = cho * 0.1  # 简单系数
        carb_bolus = 0.0

        # 确保输出不小于0，且保留足够的小数位
        total_insulin = max(0.0, output + carb_bolus)

        # 调试日志：打印计算细节 (重要：用于排查为什么输出为0)
        print(
            f"[PID_DEBUG] Params(kp={kp}, ki={ki}, kd={kd}, target={target_bg}) | "
            f"State(BG={bg}, Err={error:.2f}, Int={self.integral:.2f}, Der={derivative:.2f}) | "
            f"Terms(P={p_term:.4f}, I={i_term:.4f}, D={d_term:.4f}) -> Out={total_insulin:.4f}"
        )

        self.last_error = error
        self.last_time = timestamp

        return {
            "insulin": total_insulin,
            "basal": max(0.0, output),
            "bolus": carb_bolus,
            "iob": 0.0,  # 简化
            "cob": cho,  # 简化
        }
