import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import namedtuple
from .base_controller import BaseController

logger = logging.getLogger("SimglucoseAdapter")

# 定义模拟的 Observation 结构
Observation = namedtuple("Observation", ["CGM"])


class SimglucoseAdapter(BaseController):
    """
    适配器类：将 simglucose 的 Controller 适配到 BaseController 接口
    """

    def __init__(self, controller_instance, params: Optional[Dict] = None):
        super().__init__(params)
        self.controller = controller_instance
        self.sample_time = (
            params.get("sample_time", 3.0) if params else 3.0
        )  # 默认3分钟

        # 初始化控制器状态
        if hasattr(self.controller, "reset"):
            self.controller.reset()

    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: datetime
    ) -> Dict[str, float]:
        """
        调用 simglucose controller 的 policy 方法
        """
        # 构造 Observation
        # 注意：simglucose 通常期望 CGM 单位为 mg/dL
        # 如果传入的是 mmol/L，可能需要转换。这里假设传入已经是 mg/dL (根据 algorithm_module.py 的注释)
        obs = Observation(CGM=cgm)

        # 构造 info
        info = {
            "sample_time": self.sample_time,
            "meal": cho,
            "patient_name": "unknown",  # 可以在 params 中传入
            "time": timestamp,
        }

        # 调用 policy
        try:
            action = self.controller.policy(
                observation=obs, reward=0, done=False, **info
            )

            # 解析 Action (basal, bolus)
            # Action 通常是一个 namedtuple 或对象，有 basal 和 bolus 属性
            basal = getattr(action, "basal", 0.0)
            bolus = getattr(action, "bolus", 0.0)

            # 计算总胰岛素
            insulin = basal + bolus

            # 估算 IOB/COB (如果控制器不提供，这里只能返回0或由外部计算)
            # 这里的 adapter 主要负责计算剂量
            iob = 0.0
            cob = 0.0

            return {
                "insulin": insulin,
                "basal": basal,
                "bolus": bolus,
                "iob": iob,
                "cob": cob,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"Error executing simglucose controller: {e}")
            # 出错时返回安全值
            return {
                "insulin": 0.0,
                "basal": 0.0,
                "bolus": 0.0,
                "iob": 0.0,
                "cob": 0.0,
                "timestamp": timestamp,
            }

    def update_params(self, params: Dict):
        super().update_params(params)
        if "sample_time" in params:
            self.sample_time = params["sample_time"]

        # Update controller attributes if they exist
        for key, value in params.items():
            if hasattr(self.controller, key):
                try:
                    # Convert value to float if possible, as most params are floats
                    if isinstance(value, (int, float)):
                        setattr(self.controller, key, value)
                        logger.info(f"Updated {key} to {value}")
                    elif isinstance(value, str):
                        # Try to convert to float if it looks like a number
                        try:
                            val = float(value)
                            setattr(self.controller, key, val)
                            logger.info(f"Updated {key} to {val}")
                        except ValueError:
                            # Keep as string
                            setattr(self.controller, key, value)
                except Exception as e:
                    logger.warning(f"Failed to update {key}: {e}")
