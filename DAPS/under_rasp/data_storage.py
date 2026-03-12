"""
数据存储模块 - 内存数据缓存和状态管理
存储系统运行时的各种状态数据
"""

import threading
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import deque

from config_module import DATA_STORAGE_CONFIG

logger = logging.getLogger("DataStorage")


class DataStorage:
    """数据存储和状态管理"""

    def __init__(self, max_history: int = None):
        """
        初始化数据存储

        Args:
            max_history: 最大历史记录数
        """
        if max_history is None:
            max_history = DATA_STORAGE_CONFIG["max_history"]

        self._max_history = max_history

        # 接收数据历史
        self._received_data_history = deque(maxlen=max_history)

        # 计算结果历史
        self._calculation_history = deque(maxlen=max_history)

        # 硬件状态历史
        self._hardware_state_history = deque(maxlen=max_history)

        # 当前状态
        self._current_state = {
            # TCP数据
            "tcp_connected": False,
            "tcp_receiving": False,
            "patient_name": "",
            "timestamp": None,
            "bg": 0.0,
            "cgm": 0.0,
            "cho": 0.0,
            # 算法输出
            "insulin": 0.0,
            "basal": 0.0,
            "bolus": 0.0,
            "iob": 0.0,
            "cob": 0.0,
            # 硬件状态
            "motor_pumping": False,
            "motor_steps": 0,
            "motor_frequency": 0.0,
            "led_color": "off",
            "button_pressure": False,
            "button_normal": False,
            # 系统状态
            "system_running": False,
            "simulation_mode": False,
            "last_update": None,
        }

        # 统计信息
        self._statistics = {
            "total_received": 0,
            "total_calculations": 0,
            "total_insulin_delivered": 0.0,
            "uptime_seconds": 0.0,
            "start_time": None,
        }

        # 线程锁
        self._state_lock = threading.Lock()
        self._history_lock = threading.Lock()
        self._stats_lock = threading.Lock()

        logger.info(f"Data storage initialized (max_history={max_history})")

    # ========================================================================
    # 状态更新
    # ========================================================================

    def update_tcp_data(
        self, patient_name: str, timestamp: datetime, bg: float, cgm: float, cho: float
    ):
        """更新TCP接收的数据"""
        with self._state_lock:
            self._current_state.update(
                {
                    "patient_name": patient_name,
                    "timestamp": timestamp,
                    "bg": bg,
                    "cgm": cgm,
                    "cho": cho,
                    "tcp_receiving": True,
                    "last_update": datetime.now(),
                }
            )

        # 记录历史
        with self._history_lock:
            self._received_data_history.append(
                {
                    "timestamp": timestamp,
                    "patient_name": patient_name,
                    "bg": bg,
                    "cgm": cgm,
                    "cho": cho,
                }
            )

        # 更新统计
        with self._stats_lock:
            self._statistics["total_received"] += 1

    def update_calculation(
        self,
        insulin: float,
        basal: float,
        bolus: float,
        iob: float = 0.0,
        cob: float = 0.0,
    ):
        """更新算法计算结果"""
        with self._state_lock:
            self._current_state.update(
                {
                    "insulin": insulin,
                    "basal": basal,
                    "bolus": bolus,
                    "iob": iob,
                    "cob": cob,
                    "last_update": datetime.now(),
                }
            )

        # 记录历史
        with self._history_lock:
            self._calculation_history.append(
                {
                    "timestamp": datetime.now(),
                    "insulin": insulin,
                    "basal": basal,
                    "bolus": bolus,
                    "iob": iob,
                    "cob": cob,
                }
            )

        # 更新统计
        with self._stats_lock:
            self._statistics["total_calculations"] += 1
            self._statistics["total_insulin_delivered"] += insulin

    def update_hardware_state(self, **kwargs):
        """
        更新硬件状态

        可接受的参数:
            motor_pumping, motor_steps, motor_frequency,
            led_color, button_pressure, button_normal, etc.
        """
        with self._state_lock:
            for key, value in kwargs.items():
                if key in self._current_state:
                    self._current_state[key] = value
            self._current_state["last_update"] = datetime.now()

        # 记录历史（仅记录重要状态变化）
        if kwargs.get("motor_pumping") is not None:
            with self._history_lock:
                self._hardware_state_history.append(
                    {"timestamp": datetime.now(), **kwargs}
                )

    def update_tcp_connection(self, connected: bool):
        """更新TCP连接状态"""
        with self._state_lock:
            self._current_state["tcp_connected"] = connected

    def save_record(self, record: Dict[str, Any]):
        """
        保存完整记录（兼容性方法）

        Args:
            record: 包含patient_name, timestamp, bg, cgm, cho, insulin等字段的字典
        """
        # 提取TCP数据
        if "bg" in record or "cgm" in record:
            self.update_tcp_data(
                patient_name=record.get("patient_name", ""),
                timestamp=record.get("timestamp", datetime.now().timestamp()),
                bg=record.get("bg", 0.0),
                cgm=record.get("cgm", 0.0),
                cho=record.get("cho", 0.0),
            )

        # 提取计算结果
        if "insulin" in record:
            self.update_calculation(
                insulin=record.get("insulin", 0.0),
                basal=record.get("basal", 0.0),
                bolus=record.get("bolus", 0.0),
                iob=record.get("iob", 0.0),
                cob=record.get("cob", 0.0),
            )

        logger.debug(f"Record saved: {record.get('patient_name', 'Unknown')}")

    def update_system_state(self, **kwargs):
        """更新系统状态"""
        with self._state_lock:
            for key, value in kwargs.items():
                if key in self._current_state:
                    self._current_state[key] = value

    # ========================================================================
    # 状态查询
    # ========================================================================

    def get_current_state(self) -> Dict[str, Any]:
        """获取当前完整状态"""
        with self._state_lock:
            return self._current_state.copy()

    def get_tcp_data(self) -> Dict[str, Any]:
        """获取TCP数据"""
        with self._state_lock:
            return {
                "patient_name": self._current_state["patient_name"],
                "timestamp": self._current_state["timestamp"],
                "bg": self._current_state["bg"],
                "cgm": self._current_state["cgm"],
                "cho": self._current_state["cho"],
            }

    def get_calculation_data(self) -> Dict[str, float]:
        """获取计算数据"""
        with self._state_lock:
            return {
                "insulin": self._current_state["insulin"],
                "basal": self._current_state["basal"],
                "bolus": self._current_state["bolus"],
                "iob": self._current_state["iob"],
                "cob": self._current_state["cob"],
            }

    def get_hardware_state(self) -> Dict[str, Any]:
        """获取硬件状态"""
        with self._state_lock:
            return {
                "motor_pumping": self._current_state["motor_pumping"],
                "motor_steps": self._current_state["motor_steps"],
                "motor_frequency": self._current_state["motor_frequency"],
                "led_color": self._current_state["led_color"],
                "button_pressure": self._current_state["button_pressure"],
                "button_normal": self._current_state["button_normal"],
            }

    def get_system_state(self) -> Dict[str, Any]:
        """获取系统状态"""
        with self._state_lock:
            return {
                "system_running": self._current_state["system_running"],
                "tcp_connected": self._current_state["tcp_connected"],
                "tcp_receiving": self._current_state["tcp_receiving"],
                "simulation_mode": self._current_state["simulation_mode"],
                "last_update": self._current_state["last_update"],
            }

    # ========================================================================
    # 历史记录
    # ========================================================================

    def get_received_data_history(self, count: int = None) -> List[Dict]:
        """获取接收数据历史"""
        with self._history_lock:
            if count is None:
                return list(self._received_data_history)
            else:
                return list(self._received_data_history)[-count:]

    def get_calculation_history(self, count: int = None) -> List[Dict]:
        """获取计算结果历史"""
        with self._history_lock:
            if count is None:
                return list(self._calculation_history)
            else:
                return list(self._calculation_history)[-count:]

    def get_hardware_history(self, count: int = None) -> List[Dict]:
        """获取硬件状态历史"""
        with self._history_lock:
            if count is None:
                return list(self._hardware_state_history)
            else:
                return list(self._hardware_state_history)[-count:]

    # ========================================================================
    # 统计信息
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._statistics.copy()

            # 计算运行时间
            if stats["start_time"]:
                stats["uptime_seconds"] = (
                    datetime.now() - stats["start_time"]
                ).total_seconds()

            return stats

    def reset_statistics(self):
        """重置统计信息"""
        with self._stats_lock:
            self._statistics = {
                "total_received": 0,
                "total_calculations": 0,
                "total_insulin_delivered": 0.0,
                "uptime_seconds": 0.0,
                "start_time": datetime.now(),
            }

        logger.info("Statistics reset")

    def start_statistics(self):
        """开始统计"""
        with self._stats_lock:
            self._statistics["start_time"] = datetime.now()

    # ========================================================================
    # 清理
    # ========================================================================

    def clear_all_history(self):
        """清除所有历史记录"""
        with self._history_lock:
            self._received_data_history.clear()
            self._calculation_history.clear()
            self._hardware_state_history.clear()

        logger.info("All history cleared")

    def clear_received_history(self):
        """清除接收数据历史"""
        with self._history_lock:
            self._received_data_history.clear()

    def clear_calculation_history(self):
        """清除计算历史"""
        with self._history_lock:
            self._calculation_history.clear()

    def clear_hardware_history(self):
        """清除硬件状态历史"""
        with self._history_lock:
            self._hardware_state_history.clear()


# 测试代码
if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 创建存储
    storage = DataStorage(max_history=10)
    storage.start_statistics()

    print("Testing data storage...")

    # 模拟数据更新
    for i in range(5):
        # 更新TCP数据
        storage.update_tcp_data(
            patient_name="test_patient",
            timestamp=datetime.now(),
            bg=100.0 + i * 10,
            cgm=100.0 + i * 10,
            cho=10.0 * i,
        )

        # 更新计算结果
        storage.update_calculation(
            insulin=1.0 + i * 0.1, basal=0.8, bolus=0.2 + i * 0.1, iob=0.5, cob=20.0
        )

        # 更新硬件状态
        storage.update_hardware_state(
            motor_pumping=(i % 2 == 0), led_color="green" if i % 2 == 0 else "red"
        )

        time.sleep(0.5)

    # 查询状态
    print("\n=== Current State ===")
    state = storage.get_current_state()
    for key, value in state.items():
        print(f"{key}: {value}")

    # 查询历史
    print("\n=== Calculation History ===")
    history = storage.get_calculation_history(count=3)
    for record in history:
        print(record)

    # 查询统计
    print("\n=== Statistics ===")
    stats = storage.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")

    print("\nTest complete!")
