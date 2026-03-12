"""
电机驱动模块 - TB6600步进电机控制
使用gpiozero库，兼容所有树莓派型号
基于test_motor_gpiozero.py的成功实现
"""

import threading
import time
import logging
import os
from typing import Optional

# 设置gpiozero使用lgpio后端
os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"

try:
    from gpiozero import OutputDevice, PWMOutputDevice, RGBLED

    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("Warning: gpiozero not available, running in simulation mode")

from config_module import (
    TB6600_PUL_PIN,
    TB6600_DIR_PIN,
    MOTOR_TIME_STEP,
    MOTOR_MAX_FREQUENCY,
    calculate_insulin_to_steps,
    calculate_steps_to_insulin,
    LED_RED_PIN,
    LED_GREEN_PIN,
    LED_BLUE_PIN,
    MANUAL_JOG_FREQUENCY,
)

logger = logging.getLogger("MotorModule")


class MotorController:
    """步进电机控制器 - 基于gpiozero (已验证可工作)"""

    def __init__(self, simulation_mode: bool = False, manage_led: bool = False):
        """初始化电机控制器"""
        self.simulation_mode = simulation_mode or not HAS_GPIO
        self._step_pwm = None  # PWM输出设备
        self._dir_pin = None  # 方向引脚
        self._rgb_led = None  # RGB LED（仅当manage_led=True时使用）
        self._manage_led = manage_led
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 状态
        self._current_insulin = 0.0
        self._current_steps = 0
        self._current_frequency = 0.0
        self._is_pumping = False
        self._current_direction = "forward"
        self._state_lock = threading.Lock()

        # 目标值
        self._target_insulin = 0.0
        self._target_lock = threading.Lock()

        # ✅ 推注计时（用于自动停止）
        self._pump_start_time = 0.0
        self._pump_duration = MOTOR_TIME_STEP
        self._jog_mode = False
        self._jog_direction = 1
        self._jog_frequency = MOTOR_MAX_FREQUENCY
        self._jog_start_time = 0.0
        self._jog_insulin_rate = 0.0

        if not self.simulation_mode:
            self._setup_gpio()
        else:
            logger.warning("Motor controller running in SIMULATION mode")

    def _setup_gpio(self):
        """设置GPIO - 使用gpiozero (test_motor_gpiozero.py验证可工作)"""
        try:
            # 方向引脚
            self._dir_pin = OutputDevice(TB6600_DIR_PIN)
            self._dir_pin.on()  # 正向

            # PWM引脚
            self._step_pwm = PWMOutputDevice(TB6600_PUL_PIN, frequency=100)

            # ✅ RGB LED由系统统一管理；仅在显式要求时由电机管理
            if self._manage_led:
                self._rgb_led = RGBLED(
                    red=LED_RED_PIN,
                    green=LED_GREEN_PIN,
                    blue=LED_BLUE_PIN,
                    active_high=True,  # 共阴极LED
                )
                self._rgb_led.color = (1, 0, 0)  # 初始红色（待机）

            logger.info(
                f"✅ GPIO初始化成功 (gpiozero): PUL={TB6600_PUL_PIN}, DIR={TB6600_DIR_PIN}, LED={LED_RED_PIN}/{LED_GREEN_PIN}/{LED_BLUE_PIN}"
            )

        except Exception as e:
            logger.error(f"❌ GPIO初始化失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            self.simulation_mode = True

    def start(self) -> bool:
        """启动电机控制线程"""
        if self._running:
            logger.warning("Motor controller already running")
            return False

        self._running = True

        # 启动控制线程
        self._thread = threading.Thread(target=self._control_loop, daemon=True)
        self._thread.start()

        logger.info("✅ Motor controller started")
        return True

    def stop(self):
        """停止电机"""
        logger.info("Stopping motor controller...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)

        # 清理gpiozero设备
        if self._step_pwm:
            self._step_pwm.value = 0
            self._step_pwm.close()
        if self._dir_pin:
            self._dir_pin.close()
        if self._rgb_led:
            try:
                self._rgb_led.off()  # 关闭LED
                self._rgb_led.close()
            except Exception:
                pass

        logger.info("Motor controller stopped")

    def set_target_insulin(self, insulin: float, duration: Optional[float] = None):
        """
        设置目标胰岛素剂量并启动推注计时

        Args:
            insulin: 胰岛素剂量(单位U，负值表示反向回退)
            duration: 推注持续时间(秒)，None时使用默认时间步长
        """
        with self._target_lock:
            self._target_insulin = float(insulin)
            self._jog_mode = False
            if duration is None:
                self._pump_duration = MOTOR_TIME_STEP
            else:
                self._pump_duration = max(float(duration), 0.05)
            if insulin != 0:
                self._pump_start_time = time.time()  # 记录开始时间
            else:
                self._pump_start_time = 0.0
        logger.info(
            f"[MOTOR] 设置目标剂量: {insulin:.4f}U, duration={self._pump_duration:.2f}s"
        )

    def deliver_manual_bolus(self, insulin_units: float, duration: float) -> bool:
        """手动模式按键推注固定剂量"""
        if insulin_units <= 0 or duration <= 0:
            logger.warning("[MOTOR] 手动推注参数无效")
            return False
        self.set_target_insulin(insulin_units, duration=duration)
        logger.info(f"[MOTOR] 手动推注触发: {insulin_units:.3f}U / {duration:.2f}s")
        return True

    def reverse_for_refill(self, insulin_units: float, duration: float) -> bool:
        """换药模式快速回退"""
        if insulin_units <= 0 or duration <= 0:
            logger.warning("[MOTOR] 换药回退参数无效")
            return False
        self.set_target_insulin(-abs(insulin_units), duration=duration)
        logger.info(f"[MOTOR] 换药回退触发: {insulin_units:.3f}U / {duration:.2f}s")
        return True

    def start_manual_jog(self, frequency: Optional[float] = None):
        """手动模式持续正向推注"""
        freq = frequency if frequency is not None else MANUAL_JOG_FREQUENCY
        self._start_jog(direction=1, frequency=freq)

    def start_reverse_jog(self, frequency: Optional[float] = None):
        """以最大速度持续反转（按住按钮时调用）"""
        # 修改默认频率为 MANUAL_JOG_FREQUENCY (800Hz)，避免 5000Hz 直接启动导致堵转
        freq = frequency if frequency is not None else MANUAL_JOG_FREQUENCY
        self._start_jog(direction=-1, frequency=freq)

    def _start_jog(self, direction: int, frequency: float):
        freq = min(max(float(frequency), 1.0), MOTOR_MAX_FREQUENCY)
        rate = calculate_steps_to_insulin(freq)
        with self._target_lock:
            if self._jog_mode:
                return
            self._jog_mode = True
            self._jog_direction = 1 if direction >= 0 else -1
            self._jog_frequency = freq
            self._jog_start_time = time.time()
            self._jog_insulin_rate = rate
            self._target_insulin = 0.0
            self._pump_start_time = 0.0
        logger.info(
            f"[MOTOR] 启动持续运行 direction={'FWD' if direction >=0 else 'REV'}, "
            f"freq={freq:.1f}Hz, rate={rate:.4f}U/s"
        )

    def stop_jog(self) -> float:
        """停止持续按键运行并返回本次注入的剂量(正向为正，反向为负)"""
        with self._target_lock:
            if not self._jog_mode:
                return 0.0
            duration = max(0.0, time.time() - self._jog_start_time)
            rate = self._jog_insulin_rate
            direction = self._jog_direction
            self._jog_mode = False
            self._jog_start_time = 0.0
            self._jog_insulin_rate = 0.0
        amount = duration * rate * direction
        logger.info(
            f"[MOTOR] 退出持续运行，估算剂量={amount:.4f}U (duration={duration:.2f}s)"
        )
        return amount

    def _control_loop(self):
        """
        电机控制主循环
        ✅ 增加自动停止：推注MOTOR_TIME_STEP秒后自动清零target
        """
        logger.info("Motor control loop started")

        while self._running:
            try:
                # 获取目标值和开始时间
                with self._target_lock:
                    target_insulin = self._target_insulin
                    pump_start_time = self._pump_start_time
                    pump_duration = self._pump_duration
                    jog_mode = self._jog_mode
                    jog_direction = self._jog_direction
                    jog_frequency = self._jog_frequency

                # 持续反转模式优先
                if jog_mode:
                    direction = jog_direction
                    frequency = jog_frequency
                    with self._state_lock:
                        self._current_insulin = 0.0
                        self._current_steps = 0
                        self._current_frequency = frequency
                        self._is_pumping = True
                        self._current_direction = (
                            "forward" if direction > 0 else "reverse"
                        )

                    if not self.simulation_mode and self._step_pwm:
                        if self._dir_pin:
                            if direction > 0:
                                self._dir_pin.on()
                            else:
                                self._dir_pin.off()
                        self._step_pwm.frequency = frequency
                        self._step_pwm.value = 0.5
                        if self._rgb_led:
                            self._rgb_led.color = (1, 1, 1)
                    else:
                        logger.debug(
                            f"[SIM] 持续反转: {'FWD' if direction > 0 else 'REV'} @ {frequency:.1f}Hz"
                        )

                    time.sleep(0.05)
                    continue

                # ✅ 检查是否需要自动停止
                if target_insulin != 0 and pump_start_time > 0:
                    elapsed = time.time() - pump_start_time
                    if elapsed >= pump_duration:
                        # 推注时间到，自动清零
                        with self._target_lock:
                            self._target_insulin = 0.0
                            self._pump_start_time = 0.0
                        logger.info(f"[MOTOR] 推注完成（{elapsed:.1f}秒），自动停止")
                        target_insulin = 0.0  # 立即停止

                # 计算步数
                direction = 1 if target_insulin >= 0 else -1
                insulin_amount = abs(target_insulin)
                target_steps = calculate_insulin_to_steps(insulin_amount)

                if target_steps > 0:
                    # 计算频率
                    duration = max(pump_duration, 0.05)
                    frequency = min(max(target_steps / duration, 1), 5000)

                    # 更新状态
                    with self._state_lock:
                        self._current_insulin = target_insulin
                        self._current_steps = target_steps
                        self._current_frequency = frequency
                        self._is_pumping = True
                        self._current_direction = (
                            "forward" if direction > 0 else "reverse"
                        )

                    # 驱动电机
                    if not self.simulation_mode and self._step_pwm:
                        if self._dir_pin:
                            if direction > 0:
                                self._dir_pin.on()
                            else:
                                self._dir_pin.off()
                        self._step_pwm.frequency = frequency
                        self._step_pwm.value = 0.5  # 50%占空比

                        # 如由电机管理LED，则显示绿色（推注中）
                        if self._rgb_led:
                            self._rgb_led.color = (
                                (0, 1, 0) if direction > 0 else (1, 1, 1)
                            )

                        logger.debug(
                            f"[MOTOR] 推注中: {target_insulin:.3f}U ({'REV' if direction < 0 else 'FWD'}), "
                            f"{target_steps}步 @ {frequency:.1f}Hz"
                        )
                    else:
                        logger.debug(
                            f"[SIM] 仿真推注: {target_insulin:.3f}U ({'REV' if direction < 0 else 'FWD'}), "
                            f"{target_steps}步 @ {frequency:.1f}Hz"
                        )

                else:
                    # 停止电机
                    with self._state_lock:
                        self._current_insulin = 0.0
                        self._current_steps = 0
                        self._current_frequency = 0.0
                        self._is_pumping = False
                        self._current_direction = "forward"

                    if not self.simulation_mode and self._step_pwm:
                        self._step_pwm.value = 0
                        if self._dir_pin:
                            self._dir_pin.on()
                        # 如由电机管理LED，则显示蓝色（待机/空闲）
                        if self._rgb_led:
                            self._rgb_led.color = (0, 0, 1)

                # 控制频率：20Hz
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Motor control loop error: {e}")
                import traceback

                logger.error(traceback.format_exc())
                time.sleep(0.1)

        logger.info("Motor control loop exited")

    def get_state(self) -> dict:
        """获取电机状态"""
        with self._state_lock:
            return {
                "insulin": self._current_insulin,
                "steps": self._current_steps,
                "frequency": self._current_frequency,
                "is_pumping": self._is_pumping,
                "direction": self._current_direction,
                "simulation_mode": self.simulation_mode,
            }

    def is_pumping(self) -> bool:
        """检查是否正在推注"""
        with self._state_lock:
            return self._is_pumping

    def emergency_stop(self):
        """紧急停止"""
        logger.warning("EMERGENCY STOP triggered")
        with self._target_lock:
            self._target_insulin = 0.0
            self._pump_start_time = 0.0
            self._pump_duration = MOTOR_TIME_STEP
            self._jog_mode = False

        if not self.simulation_mode and self._step_pwm:
            self._step_pwm.value = 0

        with self._state_lock:
            self._is_pumping = False
