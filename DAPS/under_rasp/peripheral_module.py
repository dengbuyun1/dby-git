"""
外设控制模块 - 按钮和LED (使用gpiozero)
处理按钮输入和LED状态指示
gpiozero是最简单的GPIO库，支持所有树莓派型号
"""

import logging
import threading
import time
from typing import Optional, Callable

try:
    # ✅ 设置gpiozero使用lgpio作为pin factory
    import os

    os.environ["GPIOZERO_PIN_FACTORY"] = "lgpio"

    from gpiozero import RGBLED, Button

    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("Warning: gpiozero not available")

from config_module import (
    BUTTON_PRESSURE,
    BUTTON_NORMAL,
    LED_RED_PIN,
    LED_GREEN_PIN,
    LED_BLUE_PIN,
)

logger = logging.getLogger("PeripheralModule")


class PeripheralController:
    """外设控制器 - LED和按钮 (使用gpiozero)"""

    def __init__(self, simulation_mode: bool = False):
        """
        初始化外设控制器

        Args:
            simulation_mode: 仿真模式
        """
        self.simulation_mode = simulation_mode or not HAS_GPIO

        # gpiozero对象
        self._rgb_led = None
        self._button_pressure = None
        self._button_normal = None

        # 按钮回调
        self._pressure_callback: Optional[Callable] = None
        self._normal_callback: Optional[Callable] = None
        self._pressure_release_callback: Optional[Callable] = None
        self._normal_release_callback: Optional[Callable] = None

        # LED状态
        self._current_color = "off"
        self._led_lock = threading.Lock()

        # 按钮状态
        self._button_states = {
            "pressure": False,
            "normal": False,
        }
        self._button_lock = threading.Lock()

        if not self.simulation_mode:
            self._init_hardware()
        else:
            logger.warning("Peripheral controller running in SIMULATION mode")

    def _init_hardware(self):
        """初始化硬件 - 使用gpiozero"""
        try:
            logger.info(
                f"Initializing GPIO (gpiozero): R={LED_RED_PIN}, G={LED_GREEN_PIN}, B={LED_BLUE_PIN}"
            )

            # ✅ 先设置pin_factory为lgpio
            try:
                from gpiozero import Device
                from gpiozero.pins.lgpio import LGPIOFactory

                Device.pin_factory = LGPIOFactory()
                logger.info("✅ gpiozero使用lgpio后端")
            except Exception as e:
                logger.warning(f"设置pin_factory失败: {e}")

            # 创建RGB LED对象
            # active_high=True: 高电平亮（共阴极LED）
            # active_high=False: 低电平亮（共阳极LED）
            self._rgb_led = RGBLED(
                red=LED_RED_PIN,
                green=LED_GREEN_PIN,
                blue=LED_BLUE_PIN,
                active_high=True,  # 共阴极LED
            )
            logger.info("✅ RGB LED initialized")

            # 初始化为关闭
            self._rgb_led.off()

            # 创建按钮对象
            self._button_pressure = Button(
                BUTTON_PRESSURE, pull_up=True, bounce_time=0.05
            )
            self._button_normal = Button(
                BUTTON_NORMAL, pull_up=True, bounce_time=0.05
            )

            # 默认绑定事件处理函数，具体业务回调在set_button_callbacks中注册
            self._button_pressure.when_pressed = self._on_pressure_pressed
            self._button_pressure.when_released = self._on_pressure_released
            self._button_normal.when_pressed = self._on_normal_pressed
            self._button_normal.when_released = self._on_normal_released
            logger.info(
                f"✅ Buttons initialized (pressure=GPIO{BUTTON_PRESSURE}, normal=GPIO{BUTTON_NORMAL})"
            )

            logger.info("✅ Peripheral hardware initialized successfully (gpiozero)")

        except Exception as e:
            logger.error(f"❌ Peripheral initialization failed: {e}")
            import traceback

            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.warning("⚠️  Switching to SIMULATION mode")
            self.simulation_mode = True

    def set_led_color(self, color: str):
        """
        设置LED颜色 (使用gpiozero)

        Args:
            color: 颜色名称 ('red', 'green', 'blue', 'off', 等)
        """
        # 颜色映射: (R, G, B) 范围0-1
        color_map = {
            "off": (0, 0, 0),
            "red": (1, 0, 0),
            "green": (0, 1, 0),
            "blue": (0, 0, 1),
            "yellow": (1, 1, 0),
            "cyan": (0, 1, 1),
            "magenta": (1, 0, 1),
            "white": (1, 1, 1),
        }

        if color not in color_map:
            logger.warning(f"Unknown LED color: {color}")
            return

        with self._led_lock:
            self._current_color = color

        if not self.simulation_mode and self._rgb_led:
            rgb = color_map[color]

            # 设置LED颜色（gpiozero超简单！）
            self._rgb_led.color = rgb

            logger.debug(f"LED={color} RGB=({rgb[0]}, {rgb[1]}, {rgb[2]})")
        else:
            logger.debug(f"[SIM] LED={color}")

    def blink_led(self, color: str, times: int = 3, interval: float = 0.5):
        """
        闪烁LED

        Args:
            color: 颜色
            times: 闪烁次数
            interval: 闪烁间隔（秒）
        """
        for _ in range(times):
            self.set_led_color(color)
            time.sleep(interval)
            self.set_led_color("off")
            time.sleep(interval)

    def set_button_callbacks(
        self,
        pressure_callback: Optional[Callable] = None,
        normal_callback: Optional[Callable] = None,
        pressure_release_callback: Optional[Callable] = None,
        normal_release_callback: Optional[Callable] = None,
    ):
        """
        设置按钮回调函数

        Args:
            pressure_callback: 压力按钮回调
            normal_callback: 常开按钮回调
        """
        self._pressure_callback = pressure_callback
        self._normal_callback = normal_callback
        self._pressure_release_callback = pressure_release_callback
        self._normal_release_callback = normal_release_callback
        logger.info("Button callbacks registered")

        # 设置gpiozero按钮事件（如果按钮已初始化）
        if self._button_pressure:
            if pressure_callback:
                self._button_pressure.when_pressed = self._on_pressure_pressed
            if pressure_release_callback:
                self._button_pressure.when_released = self._on_pressure_released

        if self._button_normal:
            if normal_callback:
                self._button_normal.when_pressed = self._on_normal_pressed
            if normal_release_callback:
                self._button_normal.when_released = self._on_normal_released

    def _on_pressure_pressed(self):
        """压力按钮按下事件"""
        logger.info("Pressure button pressed")
        with self._button_lock:
            self._button_states["pressure"] = True
        if self._pressure_callback:
            try:
                self._pressure_callback()
            except Exception as e:
                logger.error(f"Pressure button callback error: {e}")

    def _on_pressure_released(self):
        """压力按钮释放事件"""
        logger.info("Pressure button released")
        with self._button_lock:
            self._button_states["pressure"] = False
        if self._pressure_release_callback:
            try:
                self._pressure_release_callback()
            except Exception as e:
                logger.error(f"Pressure button release callback error: {e}")

    def _on_normal_pressed(self):
        """常开按钮按下事件"""
        logger.info("Normal button pressed")
        with self._button_lock:
            self._button_states["normal"] = True
        if self._normal_callback:
            try:
                self._normal_callback()
            except Exception as e:
                logger.error(f"Normal button callback error: {e}")

    def _on_normal_released(self):
        """常开按钮释放事件"""
        logger.info("Normal button released")
        with self._button_lock:
            self._button_states["normal"] = False
        if self._normal_release_callback:
            try:
                self._normal_release_callback()
            except Exception as e:
                logger.error(f"Normal button release callback error: {e}")

    def get_button_state(self, button: str) -> bool:
        """获取按钮状态"""
        with self._button_lock:
            return self._button_states.get(button, False)

    def reset_button_state(self, button: str):
        """重置按钮状态"""
        with self._button_lock:
            if button in self._button_states:
                self._button_states[button] = False

    def get_led_color(self) -> str:
        """获取当前LED颜色"""
        with self._led_lock:
            return self._current_color

    def cleanup(self):
        """清理资源"""
        logger.info("Cleaning up peripherals...")

        if not self.simulation_mode:
            try:
                # 关闭LED
                if self._rgb_led:
                    self._rgb_led.off()
                    self._rgb_led.close()

                # 关闭按钮
                if self._button_pressure:
                    self._button_pressure.close()

                if self._button_normal:
                    self._button_normal.close()

                logger.info("Peripherals cleaned up successfully")
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
        else:
            logger.info("Peripherals cleaned up (simulation mode)")


# 测试代码
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 创建控制器
    controller = PeripheralController(simulation_mode=False)

    print("Testing LED colors...")

    try:
        # 测试LED颜色
        colors = ["red", "green", "blue", "yellow", "cyan", "magenta", "white", "off"]

        for color in colors:
            print(f"\n==> Setting LED to {color}")
            controller.set_led_color(color)
            time.sleep(2)

        # 测试闪烁
        print("\n==> Blinking red...")
        controller.blink_led("red", times=3, interval=0.5)

        print("\n✅ Test complete. Press Ctrl+C to exit...")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCleaning up...")
        controller.cleanup()
