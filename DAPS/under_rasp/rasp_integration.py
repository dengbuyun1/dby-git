"""
Raspberry Pi Integration Module - 系统整合模块

功能:
- TCP服务器：接收PC端backend发送的bg/cgm/cho/datetime数据
- 算法计算：通过algorithm_module计算实时insulin剂量
- TCP返回：将计算结果(insulin/basal/bolus)返回给backend
- 电机驱动：根据insulin值实时驱动电机模拟注射
- 硬件整合：LCD显示、LED状态指示、按钮控制

模块用法:
    from rasp_integration import RaspiIntegration

    system = RaspiIntegration(simulation=False)  # 硬件模式
    system.initialize()  # 初始化
    system.start()       # 启动主循环
    system.shutdown()    # 安全关闭

TCP协议:
    接收(backend→rasp): patient_name,timestamp,bg,cgm,cho\n
    返回(rasp→backend): insulin,basal,bolus\n

配置:
    - TCP端口: 5000 (可在config.py修改)
    - 算法参数: 在config.py的ALGORITHM_PARAMS修改

注意:
    Backend需要配置环境变量: TCP_TARGET_HOST=树莓派IP, TCP_TARGET_PORT=5000
    主程序请使用 main.py

作者: GitHub Copilot
日期: 2024
"""

import sys
import time
import signal
import logging
import threading
from typing import Optional, Dict, Any
from datetime import datetime

# 初始化日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rasp_integration.log"),
    ],
)
logger = logging.getLogger("rasp_integration")

# 动态导入模块（支持仿真）
try:
    from config_module import (
        TCP_SERVER_HOST,
        TCP_SERVER_PORT,
        ALGORITHM_PARAMS,
        MANUAL_BOLUS_UNITS,
        MANUAL_BOLUS_DURATION,
        REFILL_REVERSE_UNITS,
        REFILL_REVERSE_DURATION,
        validate_config,
        calculate_insulin_to_steps,
        calculate_steps_to_insulin,
    )
    from lcd_module import LCD1602
    from peripheral_module import PeripheralController
    from motor_module import MotorController
    from tcp_module import TCPServer

    # from algorithm_module import InsulinCalculator # 已废弃，使用新的控制器管理器
    from controllers import ControllerManager
    from data_storage import DataStorage

    logger.info("成功导入所有模块")
except ImportError as e:
    logger.warning(f"导入失败: {e}, 使用仿真模式替代类")

    # 仿真模式的空类
    class LCD1602:
        def __init__(self, simulation_mode=False):
            pass

        def start(self):
            logger.info("[SIM] LCD started")

        def display_data(self, *args, **kwargs):
            pass

        def update_message(self, msg):
            logger.info(f"[SIM] LCD: {msg}")

        def shutdown(self):
            logger.info("[SIM] LCD shutdown")

    class PeripheralController:
        def __init__(self, simulation_mode=False):
            pass

        def set_button_callbacks(self, *args, **kwargs):
            pass

        def set_led_color(self, color):
            logger.info(f"[SIM] LED: {color}")

        def shutdown(self):
            logger.info("[SIM] Peripherals shutdown")

    class MotorController:
        def __init__(self, simulation_mode=False):
            pass

        def start(self):
            logger.info("[SIM] Motor started")

        def set_target_insulin(self, insulin, duration=None):
            logger.info(f"[SIM] Motor: {insulin}U (duration={duration})")

        def get_state(self):
            return {"status": "idle", "progress": 0, "total_insulin": 0}

        def emergency_stop(self):
            logger.info("[SIM] Motor emergency stop")

        def shutdown(self):
            logger.info("[SIM] Motor shutdown")

    class TCPServer:
        def __init__(self, host, port, simulation_mode=False):
            self.host = host
            self.port = port

        def start(self, *args, **kwargs):
            # 兼容真实模块的start(data_callback=...)
            logger.info(f"[SIM] TCP Server started on {self.host}:{self.port}")

        def is_connected(self):
            return False

        def send_response(self, data):
            logger.info(f"[SIM] TCP send: {data}")

        def shutdown(self):
            logger.info("[SIM] TCP Server shutdown")

    class InsulinCalculator:
        def __init__(self, params=None):
            pass

        def calculate(self, bg, cgm, cho, timestamp):
            # 仿真算法：简单PID
            insulin = max(0, (bg - 120) * 0.05 + cho * 0.1)
            return {
                "insulin": round(insulin, 2),
                "basal": round(insulin * 0.5, 2),
                "bolus": round(insulin * 0.5, 2),
                "iob": 0.0,
                "cob": round(cho * 0.8, 1),
            }

    MANUAL_BOLUS_UNITS = 0.05
    MANUAL_BOLUS_DURATION = 0.5
    REFILL_REVERSE_UNITS = 0.3
    REFILL_REVERSE_DURATION = 0.8

    class DataStorage:
        def __init__(self, db_path=""):
            pass

        def save_record(self, data):
            logger.info(f"[SIM] Save: {data}")

        def shutdown(self):
            logger.info("[SIM] Storage shutdown")

    TCP_SERVER_HOST = "0.0.0.0"
    TCP_SERVER_PORT = 5000
    ALGORITHM_PARAMS = {
        "target_bg": 120,
        "correction_factor": 50,
        "carb_ratio": 10,
        "insulin_sensitivity": 50,
        "max_bolus": 10.0,
        "max_basal": 2.0,
    }
    validate_config = lambda: None


class RaspiIntegration:
    """
    树莓派硬件整合类（含TCP通信、算法计算、电机控制）

    数据流:
    1. TCP接收: backend发送 patient_name,timestamp,bg,cgm,cho
    2. 算法计算: InsulinCalculator.calculate() → insulin, basal, bolus
    3. TCP返回: 发送 insulin,basal,bolus 给backend
    4. 电机驱动: MotorController.set_target_insulin(insulin)
    5. 显示更新: LCD显示当前bg/insulin/状态
    """

    def __init__(self, simulation=False):
        """
        Args:
            simulation (bool): True=仿真模式（无硬件），False=真实硬件模式
        """
        self.simulation = simulation
        logger.info(f"初始化 RaspiIntegration，仿真模式={simulation}")

        # 硬件模块
        self.lcd = None  # LCD显示
        self.peripherals = None  # 按钮/LED外设
        self.motor = None  # 电机控制

        # 通信与算法模块
        self.tcp_server = None  # TCP服务器
        self.algorithm = None  # 胰岛素计算算法
        self.storage = None  # 数据存储

        # 状态变量
        self.running = False
        self.tcp_connected = False  # TCP连接状态
        self.led_blink_active = False  # LED闪烁状态
        self.led_blink_thread = None  # LED闪烁线程
        self.control_mode = "IDLE"  # 控制模式: AUTO/MANUAL/REFILL/IDLE
        self.connected_mode_preference = "AUTO"
        self.manual_bolus_units = MANUAL_BOLUS_UNITS
        self.manual_bolus_duration = MANUAL_BOLUS_DURATION
        self.refill_reverse_units = REFILL_REVERSE_UNITS
        self.refill_reverse_duration = REFILL_REVERSE_DURATION
        self.manual_override_insulin = None
        self.manual_override_lock = threading.Lock()

        # 胰岛素累积器 (用于处理微小剂量)
        self.insulin_accumulator = 0.0

        self.refill_button_active = False
        self.manual_jog_active = False
        self.last_data = {
            "patient_name": "N/A",
            "timestamp": 0,
            "bg": 0.0,
            "cgm": 0.0,
            "cho": 0.0,
            "insulin": 0.0,
            "basal": 0.0,
            "bolus": 0.0,
            "iob": 0.0,
            "cob": 0.0,
            "tcp_connected": False,
            "motor_status": "idle",
            "motor_speed": 0,  # 电机速率 0-100%
        }

    def initialize(self) -> bool:
        """初始化所有模块（硬件+TCP+算法）"""
        logger.info("开始初始化所有模块...")

        try:
            # 1. 验证配置
            validate_config()
            logger.info("配置验证通过")

            # 2. 初始化LCD显示
            logger.info("初始化LCD模块...")
            self.lcd = LCD1602(simulation_mode=self.simulation)
            self.lcd.start()
            self.lcd.update_message("System Init...")
            logger.info("✓ LCD初始化成功")

            # 3. 初始化外设（按钮/LED）
            logger.info("初始化外设模块...")
            # 使用与系统一致的仿真开关，LED由PeripheralController统一管理
            self.peripherals = PeripheralController(simulation_mode=self.simulation)
            self.peripherals.set_button_callbacks(
                pressure_callback=self._on_button1_pressed,
                normal_callback=self._on_button2_pressed,
                pressure_release_callback=self._on_button1_released,
                normal_release_callback=self._on_button2_released,
            )
            self.peripherals.set_led_color("red")  # 默认红灯等待连接
            logger.info("✓ 外设初始化成功（仿真模式）")

            # 4. 初始化电机控制
            logger.info("初始化电机模块...")
            self.motor = MotorController(simulation_mode=self.simulation)
            self.motor.start()
            logger.info("✓ 电机初始化成功")

            # 5. 初始化算法模块
            logger.info("初始化算法模块...")
            # self.algorithm = InsulinCalculator(params=ALGORITHM_PARAMS)
            self.algorithm = ControllerManager(default_params=ALGORITHM_PARAMS)
            logger.info(f"✓ 算法初始化成功，参数: {ALGORITHM_PARAMS}")

            # 6. 初始化数据存储
            logger.info("初始化数据存储...")
            # 兼容旧版DataStorage不带参数的构造函数
            try:
                self.storage = DataStorage(max_history=1000)
            except TypeError:
                self.storage = DataStorage()
            logger.info("✓ 数据存储初始化成功")

            # 7. 初始化TCP服务器
            logger.info(f"初始化TCP服务器 ({TCP_SERVER_HOST}:{TCP_SERVER_PORT})...")
            self.tcp_server = TCPServer(host=TCP_SERVER_HOST, port=TCP_SERVER_PORT)
            # 位置参数适配真实/仿真版本
            if not self.tcp_server.start(self._on_tcp_data_received):
                raise RuntimeError("TCP服务器启动失败")
            logger.info(
                f"✓ TCP服务器模块启动成功，监听 {TCP_SERVER_HOST}:{TCP_SERVER_PORT}"
            )

            # 8. 更新状态 - TCP服务器已启动，等待连接
            # TCP未连接时进入REFILL/待连接模式
            self._set_control_mode("REFILL", announce=False)
            self.lcd.update_message("Wait TCP...")
            logger.info("=" * 50)
            logger.info("所有模块初始化完成！等待TCP连接")
            logger.info("=" * 50)

            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            if self.peripherals:
                self.peripherals.set_led_color("red")  # 红色=错误
            if self.lcd:
                self.lcd.update_message(f"Init Error: {str(e)[:20]}")
            return False

    def _start_led_blink(self, interval=0.5):
        """
        启动LED闪烁（绿灯闪烁表示数据传输/电机运行）

        Args:
            interval: 闪烁间隔（秒）
        """
        if self.led_blink_active:
            return  # 已经在闪烁

        self.led_blink_active = True

        def blink_loop():
            led_state = False
            while self.led_blink_active and self.running:
                if led_state:
                    self.peripherals.set_led_color("green")
                else:
                    self.peripherals.set_led_color("off")
                led_state = not led_state
                time.sleep(interval)

            # 闪烁结束后恢复状态
            if self.running:
                self._update_led_status()

        self.led_blink_thread = threading.Thread(target=blink_loop, daemon=True)
        self.led_blink_thread.start()
        logger.debug("[LED] 开始闪烁（绿灯）")

    def _stop_led_blink(self):
        """停止LED闪烁"""
        if not self.led_blink_active:
            return

        self.led_blink_active = False
        if self.led_blink_thread:
            self.led_blink_thread.join(timeout=1.0)
        logger.debug("[LED] 停止闪烁")

    def _update_led_status(self):
        """
        更新LED状态（根据系统状态）

        规则:
        - TCP未连接 + IDLE: 红灯（等待连接）
        - TCP未连接 + REFILL: 品红静止 / 白色反转中
        - TCP已连接 AUTO: 空闲蓝 / 运行绿
        - TCP已连接 MANUAL: 空闲青 / 手动推注黄
        - 其他异常: 红
        """
        try:
            is_running = False
            try:
                if self.motor and hasattr(self.motor, "is_pumping"):
                    is_running = self.motor.is_pumping()
            except Exception as e:
                logger.debug(f"[LED] 检查电机状态失败: {e}")
                is_running = False

            color = "off"
            if not self.tcp_connected:
                if self.control_mode == "REFILL":
                    color = "white" if is_running else "magenta"
                    logger.debug("[LED] REFILL模式 (未连接)")
                elif self.control_mode == "IDLE":
                    color = "red"
                    logger.debug("[LED] 未连接 - 待机红灯")
                else:
                    color = "red"
                    logger.debug("[LED] 未连接 - 红灯")
            else:
                if self.control_mode == "MANUAL":
                    color = "yellow" if is_running else "cyan"
                    logger.debug("[LED] 手动模式")
                elif self.control_mode == "AUTO":
                    color = "green" if is_running else "blue"
                    logger.debug("[LED] 自动模式")
                elif self.control_mode == "IDLE":
                    color = "red"
                    logger.debug("[LED] 连接异常 - 回退红灯")
                else:
                    color = "white" if is_running else "magenta"
                    logger.debug("[LED] 连接状态但模式未知")

            if self.peripherals and hasattr(self.peripherals, "set_led_color"):
                self.peripherals.set_led_color(color)
        except Exception as e:
            logger.warning(f"LED状态更新失败: {e}")
            # 发生错误 - 红灯
            if self.peripherals and hasattr(self.peripherals, "set_led_color"):
                self.peripherals.set_led_color("red")

    def _set_control_mode(self, mode: str, announce: bool = True):
        """统一切换控制模式"""
        valid_modes = {"AUTO", "MANUAL", "REFILL", "IDLE"}
        mode = mode.upper()
        if mode not in valid_modes:
            logger.warning(f"[MODE] 非法模式: {mode}")
            return

        if mode == self.control_mode:
            return

        previous = self.control_mode
        self.control_mode = mode
        if mode in {"AUTO", "MANUAL"}:
            self.connected_mode_preference = mode
        if mode != "REFILL":
            self.refill_button_active = False
            if self.motor and hasattr(self.motor, "stop_jog"):
                self.motor.stop_jog()
        if mode != "MANUAL" and self.manual_jog_active:
            self._stop_manual_jog(record_override=False)
        if mode != "MANUAL":
            with self.manual_override_lock:
                self.manual_override_insulin = None

        # 切到手动模式时，停止自动推注
        if mode == "MANUAL" and previous != "MANUAL":
            if self.motor and hasattr(self.motor, "emergency_stop"):
                self.motor.emergency_stop()
                logger.info("[MODE] 切换到MANUAL，停止自动推注")
        elif mode == "IDLE":
            if self.motor and hasattr(self.motor, "emergency_stop"):
                self.motor.emergency_stop()

        if announce and self.lcd and hasattr(self.lcd, "update_message"):
            msg_map = {
                "AUTO": "MODE:AUTO",
                "MANUAL": "MODE:MANUAL",
                "REFILL": "MODE:REFILL",
                "IDLE": "MODE:IDLE",
            }
            self.lcd.update_message(msg_map.get(mode, f"MODE:{mode}"))

        self._stop_led_blink()
        self._update_led_status()
        logger.info(f"[MODE] 当前模式 → {mode}")

    def _has_recent_data(self, timeout: float = 5.0) -> bool:
        """判断TCP端是否在持续推送仿真数据"""
        if self.tcp_server and hasattr(self.tcp_server, "is_receiving_data"):
            try:
                return self.tcp_server.is_receiving_data(timeout_seconds=timeout)
            except TypeError:
                return self.tcp_server.is_receiving_data()
        return False

    def _on_tcp_data_received(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """TCP数据接收回调函数（核心数据流）"""
        try:
            logger.info(f"[TCP] 收到数据: {data}")

            # 首次检测到真实连接（tcp_module提供is_connected）
            if (
                not self.tcp_connected
                and self.tcp_server
                and hasattr(self.tcp_server, "is_connected")
                and self.tcp_server.is_connected()
            ):
                self._handle_tcp_connected()
                if self.lcd and hasattr(self.lcd, "update_message"):
                    self.lcd.update_message("TCP Connected!")

            # 1. 提取数据
            patient_name = data.get("patient_name", "Unknown")
            timestamp = float(data.get("timestamp", time.time()))
            bg = float(data.get("bg", 0.0))
            cgm = float(data.get("cgm", bg))
            cho = float(data.get("cho", 0.0))
            controller_type = data.get("controller", "default")

            # 检查是否有直接输入的胰岛素值 (例如来自回放模式)
            direct_insulin = data.get("insulin")

            # 提取PID参数
            kp = data.get("kp")
            ki = data.get("ki")
            kd = data.get("kd")
            target = data.get("target")

            # Extract new parameters
            g_lower = data.get("g_lower")
            g_upper = data.get("g_upper")
            g_safety = data.get("g_safety")
            basal_rate = data.get("basal_rate")
            pred_horizon_min = data.get("pred_horizon_min")
            control_horizon_min = data.get("control_horizon_min")
            u_min = data.get("u_min")
            u_max = data.get("u_max")
            hypo_guard = data.get("hypo_guard")
            soft_upper = data.get("soft_upper")
            basal_floor = data.get("basal_floor")
            q_bg = data.get("q_bg")
            q_low = data.get("q_low")
            w_under = data.get("w_under")
            w_over = data.get("w_over")

            # 2. 算法计算（算法需要 datetime 类型时间戳）
            result = {}

            if direct_insulin is not None:
                logger.info(f"[ALGO] 使用外部输入的胰岛素值: {direct_insulin}")
                # 如果有直接输入的胰岛素，直接使用，跳过算法计算
                result = {
                    "insulin": float(direct_insulin),
                    "basal": 0.0,
                    "bolus": float(direct_insulin),
                    "iob": float(data.get("iob", 0.0)),
                    "cob": float(data.get("cob", 0.0)),
                }
            elif self.algorithm and hasattr(self.algorithm, "calculate"):
                logger.info(
                    f"[ALGO] 开始计算: bg={bg}, cgm={cgm}, cho={cho}, ctrl={controller_type}"
                )

                # 切换控制器
                if hasattr(self.algorithm, "switch_controller"):
                    self.algorithm.switch_controller(controller_type)

                # 更新参数
                if hasattr(self.algorithm, "update_params"):
                    params_to_update = {}
                    if kp is not None:
                        params_to_update["kp"] = float(kp)
                    if ki is not None:
                        params_to_update["ki"] = float(ki)
                    if kd is not None:
                        params_to_update["kd"] = float(kd)
                    if target is not None:
                        params_to_update["target"] = float(target)

                    if g_lower is not None:
                        params_to_update["g_lower"] = float(g_lower)
                    if g_upper is not None:
                        params_to_update["g_upper"] = float(g_upper)
                    if g_safety is not None:
                        params_to_update["g_safety"] = float(g_safety)
                    if basal_rate is not None:
                        params_to_update["basal_rate"] = float(basal_rate)
                    if pred_horizon_min is not None:
                        params_to_update["pred_horizon_min"] = float(pred_horizon_min)
                    if control_horizon_min is not None:
                        params_to_update["control_horizon_min"] = float(
                            control_horizon_min
                        )
                    if u_min is not None:
                        params_to_update["u_min"] = float(u_min)
                    if u_max is not None:
                        params_to_update["u_max"] = float(u_max)
                    if hypo_guard is not None:
                        params_to_update["hypo_guard"] = float(hypo_guard)
                    if soft_upper is not None:
                        params_to_update["soft_upper"] = float(soft_upper)
                    if basal_floor is not None:
                        params_to_update["basal_floor"] = float(basal_floor)
                    if q_bg is not None:
                        params_to_update["q_bg"] = float(q_bg)
                    if q_low is not None:
                        params_to_update["q_low"] = float(q_low)
                    if w_under is not None:
                        params_to_update["w_under"] = float(w_under)
                    if w_over is not None:
                        params_to_update["w_over"] = float(w_over)

                    if params_to_update:
                        logger.info(f"[ALGO] 更新参数: {params_to_update}")
                        self.algorithm.update_params(params_to_update)

                ts_arg = timestamp
                if isinstance(timestamp, (int, float)):
                    ts_arg = datetime.fromtimestamp(timestamp)
                result = self.algorithm.calculate(
                    bg=bg, cgm=cgm, cho=cho, timestamp=ts_arg
                )
            else:
                # 回退简单策略
                insulin_est = max(0.0, (bg - 120) * 0.05 + cho * 0.1)
                result = {
                    "insulin": round(insulin_est, 2),
                    "basal": round(insulin_est * 0.5, 2),
                    "bolus": round(insulin_est * 0.5, 2),
                    "iob": 0.0,
                    "cob": round(cho * 0.8, 1),
                }

            insulin = float(result.get("insulin", 0.0))
            basal = float(result.get("basal", 0.0))
            bolus = float(result.get("bolus", 0.0))
            iob = float(result.get("iob", 0.0))
            cob = float(result.get("cob", 0.0))
            logger.info(
                f"[ALGO] 计算结果: insulin={insulin}U, basal={basal}U, bolus={bolus}U"
            )
            logger.info(f"[ALGO] IOB={iob}U, COB={cob}g")

            manual_override = None
            with self.manual_override_lock:
                if (
                    self.manual_override_insulin is not None
                    and self.control_mode == "MANUAL"
                ):
                    manual_override = self.manual_override_insulin
                    self.manual_override_insulin = None

            if manual_override is not None:
                insulin = manual_override
                basal = 0.0
                bolus = manual_override
                logger.info(
                    f"[MODE] 手动模式覆盖算法输出 -> insulin={insulin:.3f}U (返还PC)"
                )
            elif self.control_mode == "MANUAL":
                insulin = 0.0
                basal = 0.0
                bolus = 0.0
                logger.debug("[MODE] 手动模式未触发按钮，insulin=0")

            # 3. 更新内部状态
            self.last_data.update(
                {
                    "patient_name": patient_name,
                    "timestamp": timestamp,
                    "bg": bg,
                    "cgm": cgm,
                    "cho": cho,
                    "insulin": insulin,
                    "basal": basal,
                    "bolus": bolus,
                    "iob": iob,
                    "cob": cob,
                    "tcp_connected": True,
                }
            )

            # 4. 驱动电机（根据模式）
            if (
                self.control_mode == "AUTO"
                and self.motor
                and hasattr(self.motor, "set_target_insulin")
            ):
                # 累积剂量
                self.insulin_accumulator += insulin

                # 计算可执行的完整步数
                steps = calculate_insulin_to_steps(self.insulin_accumulator)

                if steps > 0:
                    # 计算实际可输注的剂量
                    insulin_to_deliver = calculate_steps_to_insulin(steps)

                    # 从累积器中扣除
                    self.insulin_accumulator -= insulin_to_deliver
                    # 避免浮点数误差导致的微小负数
                    if self.insulin_accumulator < 0:
                        self.insulin_accumulator = 0.0

                    logger.info(
                        f"[MOTOR] 自动模式 - 累积剂量足够，执行: {insulin_to_deliver:.4f}U ({steps}步)"
                    )
                    self.motor.set_target_insulin(insulin_to_deliver)
                else:
                    if insulin > 0:
                        logger.info(
                            f"[MOTOR] 剂量过小 ({insulin:.4f}U)，已累积 (当前总计: {self.insulin_accumulator:.4f}U)"
                        )
                    else:
                        logger.debug("[MOTOR] 剂量为0")

            elif insulin > 0 and self.control_mode == "MANUAL":
                logger.info(f"[MOTOR] 手动模式 - 跳过自动注射（insulin={insulin}U）")
            elif insulin > 0 and self.control_mode == "REFILL":
                logger.info(f"[MOTOR] REFILL模式 - 忽略自动剂量（insulin={insulin}U）")
            else:
                # 非自动模式或无剂量
                pass

            # 5. LED状态刷新（运行/空闲）
            self._update_led_status()

            # 6. 更新LCD
            self._update_display()

            # 7. 保存记录
            if self.storage and hasattr(self.storage, "save_record"):
                self.storage.save_record(
                    {
                        "patient_name": patient_name,
                        "timestamp": timestamp,
                        "bg": bg,
                        "cgm": cgm,
                        "cho": cho,
                        "insulin": insulin,
                        "basal": basal,
                        "bolus": bolus,
                        "iob": iob,
                        "cob": cob,
                    }
                )
                logger.info("[STORAGE] 数据已保存")

            # 8. 返回给后端
            motor_status = {}
            if self.motor and hasattr(self.motor, "get_state"):
                motor_status = self.motor.get_state()

            response = {
                "insulin": insulin,
                "basal": basal,
                "bolus": bolus,
                "hardware": {
                    "pwmDuty": 50 if motor_status.get("is_pumping") else 0,
                    "pwmFreq": motor_status.get("frequency", 0),
                    "motorStatus": (
                        "Running" if motor_status.get("is_pumping") else "Stopped"
                    ),
                    "direction": (
                        "Forward"
                        if motor_status.get("direction") == "forward"
                        else "Reverse"
                    ),
                    "actualDelivery": (
                        motor_status.get("insulin", 0)
                        if motor_status.get("is_pumping")
                        else 0
                    ),
                },
            }
            logger.info(f"[TCP] 返回数据: {response}")
            return response

        except Exception as e:
            logger.error(f"[TCP] 数据处理失败: {e}", exc_info=True)
            if self.peripherals and hasattr(self.peripherals, "set_led_color"):
                self.peripherals.set_led_color("red")
            return {"insulin": 0.0, "basal": 0.0, "bolus": 0.0}

    def _update_display(self):
        """
        更新LCD1602显示（2行×16字符）

        新布局:
        - 行1（上）：左侧显示月日(MM/DD)，右侧显示IOB（00.00格式）
        - 行2（下）：左侧显示时分秒(HH:MM:SS)，右侧显示电机实时速率（00.0格式）
        """
        try:
            # 1) 时间
            if self.last_data["timestamp"] > 0:
                from datetime import datetime

                dt = datetime.fromtimestamp(self.last_data["timestamp"])
            else:
                from datetime import datetime

                dt = datetime.now()

            md = dt.strftime("%m/%d")  # 月/日 例如 11/11 -> 5字符
            hms = dt.strftime("%H:%M:%S")  # 时:分:秒 -> 8字符

            # 2) IOB（显示在上行，00.00格式）
            iob = float(self.last_data.get("iob", 0.0))
            iob_str = f"IOB:{iob:05.2f}"  # 如 IOB:00.00 或 IOB:12.34

            # 3) 电机速率（显示在下行，00.0格式）
            freq = 0.0
            try:
                if self.motor and hasattr(self.motor, "get_state"):
                    state = self.motor.get_state()
                    if isinstance(state, dict):
                        freq = float(state.get("frequency", 0.0))
            except Exception as e:
                logger.debug(f"[LCD] 获取电机速率失败: {e}")
                freq = 0.0
            rate_str = f"Hz:{freq:04.1f}"  # 如 Hz:00.0 或 Hz:123.4

            # 行1: 左侧月日 + 右侧IOB (00.00格式)
            line1 = f"{md:<6}{iob_str:>10}"[:16]
            # 行2: 左侧时分秒 + 右侧速率 (00.0格式)
            line2 = f"{hms:<9}{rate_str:>7}"[:16]

            # 发送到LCD
            if self.lcd and hasattr(self.lcd, "display_data"):
                self.lcd.display_data(line1=line1, line2=line2)

            # 调试日志
            logger.debug(f"[LCD] Line1: '{line1}' ({len(line1)} chars)")
            logger.debug(f"[LCD] Line2: '{line2}' ({len(line2)} chars)")
            logger.debug(
                f"[LCD] Data: md={md}, time={hms}, iob={iob:.2f}, freq={freq:.1f}Hz"
            )

        except Exception as e:
            logger.warning(f"LCD更新失败: {e}")

    def _on_button1_pressed(self):
        """压力按钮：功能/模式切换"""
        logger.info("[BUTTON] 压力按钮按下 - 模式切换")

        if not self.tcp_connected:
            if self.control_mode == "REFILL":
                logger.info("[MODE] 退出换药模式，保持等待")
                self._set_control_mode("IDLE")
                if self.lcd and hasattr(self.lcd, "update_message"):
                    self.lcd.update_message("Wait TCP...")
            else:
                logger.info("[MODE] 进入换药模式")
                self._set_control_mode("REFILL")
                if self.lcd and hasattr(self.lcd, "update_message"):
                    self.lcd.update_message("Refill Ready")
            return

        if self.control_mode == "AUTO":
            self._set_control_mode("MANUAL")
        elif self.control_mode == "MANUAL":
            self._set_control_mode("AUTO")
        else:
            # REFILL恢复到上次记忆的模式
            self._set_control_mode(self.connected_mode_preference or "AUTO")

        self._update_display()

    def _on_button1_released(self):
        """压力按钮释放事件（保留日志便于调试）"""
        logger.debug("[BUTTON] 压力按钮释放")

    def _on_button2_pressed(self):
        """常开按钮：按需驱动电机"""
        logger.info("[BUTTON] 常开按钮按下 - 电机驱动请求")

        if self.control_mode == "MANUAL" and self.tcp_connected:
            self._start_manual_jog()
        elif self.control_mode == "REFILL" and not self.tcp_connected:
            if not self.refill_button_active:
                self.refill_button_active = True
                self._start_refill_reverse()
        else:
            logger.info("[MODE] 当前模式下常开按钮无效")

    def _on_button2_released(self):
        """常开按钮释放"""
        logger.info("[BUTTON] 常开按钮释放")
        if self.control_mode == "MANUAL" and self.tcp_connected:
            self._stop_manual_jog()
        elif self.control_mode == "REFILL" and not self.tcp_connected:
            self.refill_button_active = False
            self._stop_refill_reverse()

    def _trigger_manual_bolus(self):
        """执行手动模式下一次推注"""
        if not self.motor:
            logger.warning("[MODE] 电机未初始化，无法手动推注")
            return
        if not self._has_recent_data():
            logger.warning("[MODE] 无仿真数据，无法执行手动推注")
            if self.lcd and hasattr(self.lcd, "update_message"):
                self.lcd.update_message("Need simulator data")
            return
        if hasattr(self.motor, "is_pumping") and self.motor.is_pumping():
            logger.info("[MODE] 电机忙，跳过本次手动推注")
            return

        units = max(0.0, float(self.manual_bolus_units))
        duration = max(0.0, float(self.manual_bolus_duration))
        if units == 0 or duration == 0:
            logger.warning("[MODE] 手动推注参数未配置")
            return

        success = False
        if hasattr(self.motor, "deliver_manual_bolus"):
            success = self.motor.deliver_manual_bolus(units, duration)
        else:
            self.motor.set_target_insulin(units, duration=duration)
            success = True

        if success:
            logger.info(f"[MODE] 手动推注 {units:.3f}U")
            with self.manual_override_lock:
                self.manual_override_insulin = units
            if self.lcd and hasattr(self.lcd, "update_message"):
                self.lcd.update_message(f"Manual {units:.2f}U")
            self._update_led_status()
        return success

    def _start_manual_jog(self):
        """手动模式：按住常开按钮开始持续推注"""
        if not self.motor:
            logger.warning("[MODE] 电机未初始化，无法手动推注")
            return
        if not self._has_recent_data():
            logger.warning("[MODE] 未检测到前端数据，无法手动推注")
            if self.lcd and hasattr(self.lcd, "update_message"):
                self.lcd.update_message("Need simulator data")
            return
        if self.manual_jog_active:
            return

        if hasattr(self.motor, "start_manual_jog"):
            self.motor.start_manual_jog()
            self.manual_jog_active = True
            if self.lcd and hasattr(self.lcd, "update_message"):
                self.lcd.update_message("Manual Infusing...")
            logger.info("[MODE] 手动模式持续推注开始")
        else:
            # 旧版电机不支持jog，退化为固定剂量
            if self._trigger_manual_bolus():
                logger.info("[MODE] 手动模式退化为固定剂量推注")

    def _stop_manual_jog(self, record_override: bool = True):
        """松开常开按钮，停止持续推注并记录剂量"""
        amount = 0.0
        if self.motor and hasattr(self.motor, "stop_jog"):
            amount = self.motor.stop_jog()
        self.manual_jog_active = False

        if not record_override:
            with self.manual_override_lock:
                self.manual_override_insulin = None
            return

        amount = max(0.0, amount)
        if amount > 0:
            with self.manual_override_lock:
                self.manual_override_insulin = amount
            if self.lcd and hasattr(self.lcd, "update_message"):
                self.lcd.update_message(f"Manual {amount:.2f}U")
            logger.info(f"[MODE] 手动持续推注完成，剂量={amount:.3f}U")
            self._update_led_status()
        else:
            with self.manual_override_lock:
                self.manual_override_insulin = None

    def _start_refill_reverse(self):
        """按住常开按钮时启动换药反转"""
        if not self.motor:
            logger.warning("[MODE] 电机未初始化，无法回退")
            return
        if self.control_mode != "REFILL":
            return

        if hasattr(self.motor, "start_reverse_jog"):
            self.motor.start_reverse_jog()
            logger.info("[MODE] 换药模式 - 持续反转中")
        else:
            units = max(0.0, float(self.refill_reverse_units))
            duration = max(0.1, float(self.refill_reverse_duration))
            self.motor.set_target_insulin(-units, duration=duration)
            logger.info(f"[MODE] 换药模式（兼容） - 反转 {units:.3f}U/{duration:.2f}s")

        if self.lcd and hasattr(self.lcd, "update_message"):
            self.lcd.update_message("Reverse Running")
        self._update_led_status()

    def _stop_refill_reverse(self):
        """松开常开按钮时停止换药反转"""
        if not self.motor or self.control_mode != "REFILL":
            return
        if hasattr(self.motor, "stop_jog"):
            self.motor.stop_jog()
        else:
            if hasattr(self.motor, "emergency_stop"):
                self.motor.emergency_stop()
        if self.lcd and hasattr(self.lcd, "update_message"):
            self.lcd.update_message("Refill Ready")
        self._update_led_status()

    def _handle_tcp_connected(self):
        """处理TCP建立事件"""
        logger.info("[TCP] 客户端已连接")
        self.tcp_connected = True
        target_mode = self.connected_mode_preference or "AUTO"
        self._set_control_mode(target_mode, announce=False)
        self._update_led_status()

    def _handle_tcp_disconnected(self):
        """处理TCP断开事件"""
        logger.warning("[TCP] 客户端断开")
        self.tcp_connected = False
        with self.manual_override_lock:
            self.manual_override_insulin = None
        if self.manual_jog_active:
            self._stop_manual_jog(record_override=False)
        self._set_control_mode("IDLE", announce=False)
        if self.motor and hasattr(self.motor, "stop_jog"):
            self.motor.stop_jog()
        self._update_led_status()

    def start(self):
        """启动主循环（保持系统运行）"""
        logger.info("启动主循环...")
        self.running = True

        try:
            last_tcp_check = time.time()
            tcp_check_interval = 5.0  # 每5秒检查一次TCP连接状态

            while self.running:
                try:
                    # 主循环：定期更新显示和检查状态
                    self._update_display()

                    # 定期检查TCP连接状态
                    current_time = time.time()
                    if current_time - last_tcp_check >= tcp_check_interval:
                        # 检查TCP连接状态
                        is_connected = (
                            self.tcp_server
                            and hasattr(self.tcp_server, "is_connected")
                            and self.tcp_server.is_connected()
                        )

                        # 更新连接状态标志
                        if is_connected and not self.tcp_connected:
                            # 从未连接变为已连接
                            self._handle_tcp_connected()
                            if self.lcd and hasattr(self.lcd, "update_message"):
                                self.lcd.update_message("TCP Connected")
                        elif not is_connected and self.tcp_connected:
                            # 从已连接变为未连接
                            self._handle_tcp_disconnected()
                            if self.lcd and hasattr(self.lcd, "update_message"):
                                self.lcd.update_message("Wait TCP...")

                        # 检查是否长时间未收到数据（已连接但空闲）
                        if is_connected:
                            # 有连接，但检查是否超时
                            if self.last_data.get("timestamp", 0) > 0:
                                time_since_last_data = (
                                    current_time - self.last_data["timestamp"]
                                )
                                if time_since_last_data > 30:  # 30秒未收到数据
                                    logger.warning(
                                        f"[TCP] {time_since_last_data:.0f}秒未收到数据，可能连接空闲"
                                    )
                                    # 仅更新LCD提示，不直接断开状态（保持蓝灯）
                                    if self.lcd:
                                        self.lcd.update_message("TCP Idle...")
                            else:
                                # 已连接但尚无数据
                                if self.lcd and hasattr(self.lcd, "update_message"):
                                    self.lcd.update_message("TCP Connected")

                        last_tcp_check = current_time

                    time.sleep(1)  # 1秒更新一次

                except Exception as e:
                    logger.error(f"主循环错误: {e}")
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("接收到Ctrl+C，准备退出...")
        finally:
            self.shutdown()

    def shutdown(self):
        """关闭所有模块"""
        logger.info("开始关闭所有模块...")
        self.running = False

        # 停止LED闪烁
        self._stop_led_blink()

        if self.lcd and hasattr(self.lcd, "update_message"):
            self.lcd.update_message("Shutting down...")

        # 按顺序关闭各模块
        if self.motor and hasattr(self.motor, "stop"):
            self.motor.stop()  # MotorController使用stop()方法,不是shutdown()
            logger.info("✓ 电机已关闭")

        if self.tcp_server and hasattr(self.tcp_server, "shutdown"):
            self.tcp_server.shutdown()
            logger.info("✓ TCP服务器已关闭")

        if self.storage and hasattr(self.storage, "shutdown"):
            self.storage.shutdown()
            logger.info("✓ 数据存储已关闭")

        if self.peripherals:
            if hasattr(self.peripherals, "set_led_color"):
                self.peripherals.set_led_color("off")
            if hasattr(self.peripherals, "cleanup"):
                self.peripherals.cleanup()  # PeripheralController使用cleanup()方法
            logger.info("✓ 外设已关闭")

        if self.lcd and hasattr(self.lcd, "shutdown"):
            self.lcd.shutdown()
            logger.info("✓ LCD已关闭")

        logger.info("=" * 50)
        logger.info("系统已安全关闭")
        logger.info("=" * 50)
