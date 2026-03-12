"""
控制器基类定义
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from datetime import datetime


class BaseController(ABC):
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}

    def update_params(self, params: Dict):
        """更新控制器参数"""
        if params:
            self.params.update(params)

    @abstractmethod
    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: datetime
    ) -> Dict[str, float]:
        """
        计算胰岛素剂量
        Returns:
            Dict containing: insulin, basal, bolus, iob, cob
        """
        pass

    def update_params(self, params: Dict):
        """更新参数"""
        self.params.update(params)
