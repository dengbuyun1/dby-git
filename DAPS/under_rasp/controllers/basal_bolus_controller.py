"""
Basal-Bolus 控制器实现 (基于原有 algorithm_module.py)
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import threading
from .base_controller import BaseController


class BasalBolusController(BaseController):
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        # 默认参数
        self.default_params = {
            "target_bg": 120.0,
            "basal_base": 0.0,
            "basal_kp": 0.0,
            "carb_ratio": 15.0,
            "correction_factor": 50.0,
            "iob_sensitivity": 1.0,
            "cob_boost": 0.5,
            "dia": 4.0,
        }
        if params:
            self.default_params.update(params)
        self.params = self.default_params

        self._insulin_history = deque(maxlen=1000)
        self._carb_history = deque(maxlen=1000)
        self._history_lock = threading.Lock()

    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: datetime
    ) -> Dict[str, float]:
        if cho > 0:
            self._add_carb_intake(timestamp, cho)

        iob = self._calculate_iob(timestamp)
        cob = self._calculate_cob(timestamp)
        basal = self._calculate_basal(bg, iob)
        bolus = self._calculate_bolus(bg, cho, iob, cob)
        insulin = basal + bolus

        if insulin > 0:
            self._add_insulin_dose(timestamp, basal, bolus)

        return {
            "insulin": insulin,
            "basal": basal,
            "bolus": bolus,
            "iob": iob,
            "cob": cob,
        }

    def _add_carb_intake(self, timestamp: datetime, amount: float):
        with self._history_lock:
            self._carb_history.append((timestamp, amount))

    def _add_insulin_dose(self, timestamp: datetime, basal: float, bolus: float):
        with self._history_lock:
            self._insulin_history.append((timestamp, basal, bolus))

    def _calculate_basal(self, bg: float, iob: float) -> float:
        target_bg = self.params["target_bg"]
        basal_base = self.params["basal_base"]
        kp = self.params["basal_kp"]
        error = bg - target_bg
        basal = basal_base + kp * error
        return max(0.0, basal)

    def _calculate_bolus(self, bg: float, cho: float, iob: float, cob: float) -> float:
        target_bg = self.params["target_bg"]
        carb_ratio = self.params["carb_ratio"]
        correction_factor = self.params["correction_factor"]
        iob_sensitivity = self.params["iob_sensitivity"]
        cob_boost = self.params["cob_boost"]

        carb_bolus = cho / carb_ratio if cho > 0 else 0.0
        error = bg - target_bg
        correction = max(0.0, error / correction_factor)
        iob_suppression = iob * iob_sensitivity
        cob_enhancement = (cob * cob_boost) / carb_ratio if cob > 0 else 0.0

        bolus = carb_bolus + correction - iob_suppression + cob_enhancement
        return max(0.0, bolus)

    def _calculate_iob(self, current_time: datetime) -> float:
        dia = self.params["dia"]
        iob = 0.0
        with self._history_lock:
            for timestamp, basal, bolus in self._insulin_history:
                if isinstance(current_time, datetime) and isinstance(
                    timestamp, datetime
                ):
                    elapsed_seconds = (current_time - timestamp).total_seconds()
                elif isinstance(current_time, datetime):
                    elapsed_seconds = current_time.timestamp() - timestamp
                elif isinstance(timestamp, datetime):
                    elapsed_seconds = current_time - timestamp.timestamp()
                else:
                    elapsed_seconds = current_time - timestamp

                elapsed_hours = elapsed_seconds / 3600
                if 0 <= elapsed_hours < dia:
                    activity = 1.0 - (elapsed_hours / dia)
                    iob += (basal + bolus) * activity
        return iob

    def _calculate_cob(self, current_time: datetime) -> float:
        # 简化版COB计算
        cob = 0.0
        absorption_time = 3.0  # 假设3小时吸收完
        with self._history_lock:
            for timestamp, amount in self._carb_history:
                if isinstance(current_time, datetime) and isinstance(
                    timestamp, datetime
                ):
                    elapsed_seconds = (current_time - timestamp).total_seconds()
                elif isinstance(current_time, datetime):
                    elapsed_seconds = current_time.timestamp() - timestamp
                elif isinstance(timestamp, datetime):
                    elapsed_seconds = current_time - timestamp.timestamp()
                else:
                    elapsed_seconds = current_time - timestamp

                elapsed_hours = elapsed_seconds / 3600
                if 0 <= elapsed_hours < absorption_time:
                    remaining = 1.0 - (elapsed_hours / absorption_time)
                    cob += amount * remaining
        return cob
