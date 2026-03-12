"""
控制器管理器
"""

import logging
from typing import Dict, Optional
from datetime import datetime
from .base_controller import BaseController
from .pid_controller import PidController
from .basal_bolus_controller import BasalBolusController
from .simglucose_adapter import SimglucoseAdapter

# 导入新算法
try:
    from .arx_zone_mpc import ARXRLSZoneMPCController
    from .safe_pid_sim import SafetyFirstPID
    from .simple_mpc import SimpleMPCController
    from .zone_mpc import ZoneMPCController

    HAS_SIMGLUCOSE_CONTROLLERS = True
except ImportError:
    HAS_SIMGLUCOSE_CONTROLLERS = False
    print("Warning: Could not import simglucose controllers (missing dependencies?)")

logger = logging.getLogger("ControllerManager")


class ControllerManager:
    def __init__(self, default_params: Optional[Dict] = None):
        self.params = default_params or {}
        self.controllers: Dict[str, BaseController] = {
            "PID": PidController({}),  # 不使用默认参数，完全依赖上位机下发
            "Basal-Bolus": BasalBolusController(self.params),
            "MPC": BasalBolusController(self.params),  # 暂时用Basal-Bolus代替MPC
            "default": BasalBolusController(self.params),
        }

        # 注册新算法
        if HAS_SIMGLUCOSE_CONTROLLERS:
            self.controllers["ARX-Zone-MPC"] = SimglucoseAdapter(
                ARXRLSZoneMPCController(), self.params
            )
            self.controllers["Safe-PID"] = SimglucoseAdapter(
                SafetyFirstPID(), self.params
            )
            self.controllers["Simple-MPC"] = SimglucoseAdapter(
                SimpleMPCController(), self.params
            )
            self.controllers["Zone-MPC"] = SimglucoseAdapter(
                ZoneMPCController(), self.params
            )

        self.current_controller_name = "default"

        self.current_controller = self.controllers["default"]

    def switch_controller(self, name: str):
        """切换控制器"""
        # 忽略大小写
        target_name = name
        for key in self.controllers.keys():
            if key.lower() == name.lower():
                target_name = key
                break

        if target_name in self.controllers:
            if self.current_controller_name != target_name:
                logger.info(
                    f"Switching controller from {self.current_controller_name} to {target_name}"
                )
                self.current_controller_name = target_name
                self.current_controller = self.controllers[target_name]
        else:
            logger.warning(f"Controller {name} not found, using default")
            self.current_controller_name = "default"
            self.current_controller = self.controllers["default"]

    def update_params(self, params: Dict):
        """更新当前控制器的参数"""
        if self.current_controller:
            self.current_controller.update_params(params)

    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: datetime
    ) -> Dict[str, float]:
        return self.current_controller.calculate(bg, cgm, cho, timestamp)
