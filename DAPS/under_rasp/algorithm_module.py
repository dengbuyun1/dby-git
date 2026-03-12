"""
算法模块 - 胰岛素剂量计算
实现基于PID的血糖控制算法（预留接口可扩展为更复杂算法）
"""

import logging
import threading
from typing import Dict, Optional
from datetime import datetime, timedelta
from collections import deque

from config_module import ALGORITHM_PARAMS

logger = logging.getLogger("AlgorithmModule")


class InsulinCalculator:
    """胰岛素剂量计算器"""

    def __init__(self, params: Optional[Dict] = None):
        """
        初始化算法模块

        Args:
            params: 算法参数字典，如果为None则使用默认配置
        """
        self.params = params or ALGORITHM_PARAMS.copy()

        # IOB/COB 跟踪
        self._insulin_history = deque(maxlen=1000)  # (timestamp, basal, bolus)
        self._carb_history = deque(maxlen=1000)  # (timestamp, carbs)
        self._history_lock = threading.Lock()

        # 当前计算值
        self._latest_calculation = {
            "insulin": 0.0,
            "basal": 0.0,
            "bolus": 0.0,
            "iob": 0.0,
            "cob": 0.0,
            "timestamp": None,
        }
        self._calc_lock = threading.Lock()

        logger.info("Insulin calculator initialized with params: %s", self.params)

    def calculate(
        self, bg: float, cgm: float, cho: float, timestamp: Optional[datetime] = None
    ) -> Dict[str, float]:
        """
        计算胰岛素剂量

        Args:
            bg: 血糖值 (mg/dL)
            cgm: CGM读数 (mg/dL)
            cho: 碳水摄入 (g)
            timestamp: 时间戳

        Returns:
            包含insulin, basal, bolus的字典
        """
        if timestamp is None:
            timestamp = datetime.now()

        # 记录碳水摄入
        if cho > 0:
            self._add_carb_intake(timestamp, cho)

        # 计算IOB和COB
        iob = self._calculate_iob(timestamp)
        cob = self._calculate_cob(timestamp)

        # 计算基础率
        basal = self._calculate_basal(bg, iob)

        # 计算餐时大剂量
        bolus = self._calculate_bolus(bg, cho, iob, cob)

        # 总胰岛素
        insulin = basal + bolus

        # 记录胰岛素剂量
        if insulin > 0:
            self._add_insulin_dose(timestamp, basal, bolus)

        # 保存计算结果
        with self._calc_lock:
            self._latest_calculation = {
                "insulin": insulin,
                "basal": basal,
                "bolus": bolus,
                "iob": iob,
                "cob": cob,
                "timestamp": timestamp,
            }

        logger.debug(
            f"Calculated: BG={bg:.1f} -> I={insulin:.3f} (B={basal:.3f}, L={bolus:.3f}), "
            f"IOB={iob:.3f}, COB={cob:.1f}"
        )

        return {
            "insulin": insulin,
            "basal": basal,
            "bolus": bolus,
            "iob": iob,
            "cob": cob,
        }

    def _calculate_basal(self, bg: float, iob: float) -> float:
        """
        计算基础率

        Args:
            bg: 血糖值
            iob: 体内活性胰岛素

        Returns:
            基础率 (U)
        """
        target_bg = self.params["target_bg"]
        basal_base = self.params["basal_base"]
        kp = self.params["basal_kp"]

        # PID控制（简化版，仅P项）
        error = bg - target_bg
        basal = basal_base + kp * error

        # 限制在合理范围
        return max(0.0, basal)

    def _calculate_bolus(self, bg: float, cho: float, iob: float, cob: float) -> float:
        """
        计算餐时大剂量

        Args:
            bg: 血糖值
            cho: 碳水摄入
            iob: 体内活性胰岛素
            cob: 未吸收碳水

        Returns:
            餐时大剂量 (U)
        """
        target_bg = self.params["target_bg"]
        carb_ratio = self.params["carb_ratio"]
        correction_factor = self.params["correction_factor"]
        iob_sensitivity = self.params["iob_sensitivity"]
        cob_boost = self.params["cob_boost"]

        # 碳水覆盖
        carb_bolus = cho / carb_ratio if cho > 0 else 0.0

        # 高血糖校正
        error = bg - target_bg
        correction = max(0.0, error / correction_factor)

        # IOB抑制（避免叠加性低血糖）
        iob_suppression = iob * iob_sensitivity

        # COB增强（应对未吸收碳水）
        cob_enhancement = (cob * cob_boost) / carb_ratio if cob > 0 else 0.0

        # 总餐时剂量
        bolus = carb_bolus + correction - iob_suppression + cob_enhancement

        return max(0.0, bolus)

    def _calculate_iob(self, current_time: datetime) -> float:
        """
        计算体内活性胰岛素（IOB）
        使用双指数衰减模型

        Args:
            current_time: 当前时间

        Returns:
            IOB (U)
        """
        dia = self.params["dia"]  # 胰岛素作用时间（小时）
        iob = 0.0

        with self._history_lock:
            for timestamp, basal, bolus in self._insulin_history:
                # 计算时间差（秒），支持 datetime 和 float 两种类型
                if isinstance(current_time, datetime) and isinstance(
                    timestamp, datetime
                ):
                    elapsed_seconds = (current_time - timestamp).total_seconds()
                elif isinstance(current_time, datetime):
                    # current_time 是 datetime，timestamp 是 float
                    elapsed_seconds = current_time.timestamp() - timestamp
                elif isinstance(timestamp, datetime):
                    # current_time 是 float，timestamp 是 datetime
                    elapsed_seconds = current_time - timestamp.timestamp()
                else:
                    # 都是 float
                    elapsed_seconds = current_time - timestamp

                elapsed_hours = elapsed_seconds / 3600

                if elapsed_hours >= dia:
                    continue

                # 双指数衰减模型
                # IOB(t) = Dose × [0.65×e^(-t/1.2h) + 0.35×e^(-t/3h)]
                dose = basal + bolus
                fast_decay = 0.65 * (2.71828 ** (-elapsed_hours / 1.2))
                slow_decay = 0.35 * (2.71828 ** (-elapsed_hours / 3.0))
                iob += dose * (fast_decay + slow_decay)

        return iob

    def _calculate_cob(self, current_time: datetime) -> float:
        """
        计算未吸收碳水（COB）
        使用抛物线吸收模型

        Args:
            current_time: 当前时间

        Returns:
            COB (g)
        """
        absorption_time = self.params["carb_absorption_time"]  # 碳水吸收时间(小时)
        cob = 0.0

        with self._history_lock:
            for timestamp, carbs in self._carb_history:
                # 处理timestamp可能是datetime或float的情况
                if isinstance(current_time, datetime) and isinstance(
                    timestamp, datetime
                ):
                    elapsed_seconds = (current_time - timestamp).total_seconds()
                elif isinstance(current_time, datetime):
                    # current_time是datetime, timestamp是float
                    elapsed_seconds = current_time.timestamp() - timestamp
                elif isinstance(timestamp, datetime):
                    # current_time是float, timestamp是datetime
                    elapsed_seconds = current_time - timestamp.timestamp()
                else:
                    # 两者都是float
                    elapsed_seconds = current_time - timestamp

                elapsed_hours = elapsed_seconds / 3600

                if elapsed_hours >= absorption_time:
                    continue

                # 抛物线吸收模型
                # COB(t) = CHO × max(0, 1 - t/T)²
                fraction = 1.0 - (elapsed_hours / absorption_time)
                cob += carbs * max(0.0, fraction) ** 2

        return cob

    def _add_insulin_dose(self, timestamp: datetime, basal: float, bolus: float):
        """记录胰岛素剂量"""
        with self._history_lock:
            self._insulin_history.append((timestamp, basal, bolus))

    def _add_carb_intake(self, timestamp: datetime, carbs: float):
        """记录碳水摄入"""
        with self._history_lock:
            self._carb_history.append((timestamp, carbs))

    def get_latest_calculation(self) -> Dict:
        """获取最新计算结果"""
        with self._calc_lock:
            return self._latest_calculation.copy()

    def get_iob_cob(self, timestamp: Optional[datetime] = None) -> tuple:
        """
        获取当前IOB和COB

        Returns:
            (iob, cob)
        """
        if timestamp is None:
            timestamp = datetime.now()

        iob = self._calculate_iob(timestamp)
        cob = self._calculate_cob(timestamp)

        return (iob, cob)

    def clear_history(self):
        """清除历史记录"""
        with self._history_lock:
            self._insulin_history.clear()
            self._carb_history.clear()

        logger.info("History cleared")

    def update_params(self, **kwargs):
        """更新算法参数"""
        for key, value in kwargs.items():
            if key in self.params:
                old_value = self.params[key]
                self.params[key] = value
                logger.info(f"Parameter updated: {key} = {value} (was {old_value})")
            else:
                logger.warning(f"Unknown parameter: {key}")


# 测试代码
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 创建计算器
    calculator = InsulinCalculator()

    print("Testing insulin calculator...")

    # 测试场景1: 正常血糖，无碳水
    result = calculator.calculate(bg=110.0, cgm=110.0, cho=0.0)
    print(f"\nScenario 1 - Normal BG: {result}")

    # 测试场景2: 高血糖
    result = calculator.calculate(bg=180.0, cgm=180.0, cho=0.0)
    print(f"\nScenario 2 - High BG: {result}")

    # 测试场景3: 餐食
    result = calculator.calculate(bg=110.0, cgm=110.0, cho=60.0)
    print(f"\nScenario 3 - Meal: {result}")

    # 测试场景4: 高血糖 + 餐食
    result = calculator.calculate(bg=180.0, cgm=180.0, cho=60.0)
    print(f"\nScenario 4 - High BG + Meal: {result}")

    # 检查IOB
    # time.sleep(1)
    iob, cob = calculator.get_iob_cob()
    print(f"\nIOB: {iob:.3f}U, COB: {cob:.1f}g")

    # 测试场景5: 有IOB时的血糖控制
    result = calculator.calculate(bg=140.0, cgm=140.0, cho=0.0)
    print(f"\nScenario 5 - With IOB: {result}")

    print("\nTest complete!")
