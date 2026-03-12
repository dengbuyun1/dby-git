"""
LCD1602显示模块 - I2C接口
显示系统状态、血糖值和胰岛素剂量
"""

import threading
import time
import logging
from typing import Optional
from datetime import datetime

try:
    from smbus2 import SMBus

    HAS_I2C = True
except ImportError:
    HAS_I2C = False
    print("Warning: smbus2 not available, LCD display disabled")

from config_module import (
    LCD_I2C_BUS,
    LCD_I2C_ADDRESS,
    LCD_CONFIG,
)

logger = logging.getLogger("LCDModule")


# LCD1602 命令
LCD_CMD = 0x00
LCD_CHR = 0x01
LCD_BACKLIGHT = 0x08
LCD_ENABLE = 0x04

# 延时参数
E_PULSE = 0.0005
E_DELAY = 0.0005


class LCD1602:
    """LCD1602 显示控制器（I2C接口）"""

    def __init__(
        self,
        bus_id: int = LCD_I2C_BUS,
        address: int = LCD_I2C_ADDRESS,
        simulation_mode: bool = False,
    ):
        """
        初始化LCD显示器

        Args:
            bus_id: I2C总线编号
            address: I2C设备地址
            simulation_mode: 仿真模式
        """
        self.bus_id = bus_id
        self.address = address
        self.simulation_mode = simulation_mode or not HAS_I2C
        self._bus: Optional[SMBus] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # 显示内容
        self._line1 = ""
        self._line2 = ""
        self._display_lock = threading.Lock()

        # 显示模式
        self._display_mode = 0  # 0: 状态信息, 1: 详细数据
        self._last_toggle = time.time()

        if not self.simulation_mode:
            self._init_i2c()
        else:
            logger.warning("LCD running in SIMULATION mode")

    def _init_i2c(self):
        """初始化I2C总线和LCD"""
        try:
            self._bus = SMBus(self.bus_id)

            # 初始化LCD（4位模式）
            self._write_byte(0x33, LCD_CMD)
            self._write_byte(0x32, LCD_CMD)
            self._write_byte(0x06, LCD_CMD)
            self._write_byte(0x0C, LCD_CMD)
            self._write_byte(0x28, LCD_CMD)
            self._write_byte(0x01, LCD_CMD)
            time.sleep(E_DELAY)

            logger.info(
                f"LCD initialized: bus={self.bus_id}, addr=0x{self.address:02X}"
            )

        except Exception as e:
            logger.error(f"LCD initialization failed: {e}")
            self.simulation_mode = True

    def _write_byte(self, data: int, mode: int):
        """写入一个字节到LCD"""
        if self.simulation_mode or not self._bus:
            return

        try:
            with self._lock:
                high_bits = mode | (data & 0xF0) | LCD_BACKLIGHT
                low_bits = mode | ((data << 4) & 0xF0) | LCD_BACKLIGHT

                # 高4位
                self._bus.write_byte(self.address, high_bits)
                self._toggle_enable(high_bits)

                # 低4位
                self._bus.write_byte(self.address, low_bits)
                self._toggle_enable(low_bits)

        except Exception as e:
            # 写入失败就切换到仿真模式,不要疯狂重试!
            if not self.simulation_mode:
                logger.error(f"LCD写入失败,切换到仿真模式: {e}")
                self.simulation_mode = True

    def _toggle_enable(self, data: int):
        """切换使能信号"""
        if self.simulation_mode or not self._bus:
            return

        try:
            time.sleep(E_DELAY)
            self._bus.write_byte(self.address, data | LCD_ENABLE)
            time.sleep(E_PULSE)
            self._bus.write_byte(self.address, data & ~LCD_ENABLE)
            time.sleep(E_DELAY)
        except Exception as e:
            # 出错就停止,不要递归重试
            if not self.simulation_mode:
                logger.error(f"LCD toggle失败: {e}")
                self.simulation_mode = True
                raise

    def clear(self):
        """清屏"""
        self._write_byte(0x01, LCD_CMD)
        time.sleep(E_DELAY)

    def set_cursor(self, line: int, column: int):
        """
        设置光标位置

        Args:
            line: 行号 (1 或 2)
            column: 列号 (0-15)
        """
        if line == 1:
            address = 0x80 + column
        elif line == 2:
            address = 0xC0 + column
        else:
            return

        self._write_byte(address, LCD_CMD)

    def write_string(self, text: str, line: int = 1):
        """
        在指定行写入字符串

        Args:
            text: 要显示的文本（最多16字符）
            line: 行号 (1 或 2)
        """
        # 截断或补齐到16字符
        text = text[:16].ljust(16)

        # 保存到缓冲区
        with self._display_lock:
            if line == 1:
                self._line1 = text
            elif line == 2:
                self._line2 = text

        # 显示
        if not self.simulation_mode:
            self.set_cursor(line, 0)
            for char in text:
                self._write_byte(ord(char), LCD_CHR)
        else:
            logger.debug(f"[LCD Line{line}] {text}")

    def start(self) -> bool:
        """启动LCD刷新线程"""
        if self._running:
            logger.warning("LCD already running")
            return False

        self._running = True

        # 启动刷新线程
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()

        # 显示欢迎信息
        self.write_string("DAPS System", 1)
        self.write_string("Initializing...", 2)

        logger.info("LCD display started")
        return True

    def stop(self):
        """停止LCD"""
        logger.info("Stopping LCD display...")
        self._running = False

        if self._thread:
            self._thread.join(timeout=2)

        # 清屏
        self.clear()

        # 关闭I2C
        if not self.simulation_mode and self._bus:
            self._bus.close()

        logger.info("LCD display stopped")

    def _refresh_loop(self):
        """刷新循环（处理显示轮换）"""
        while self._running:
            try:
                # 检查是否需要切换显示模式
                current_time = time.time()
                if isinstance(self._last_toggle, (int, float)):
                    if current_time - self._last_toggle > LCD_CONFIG["toggle_interval"]:
                        self._display_mode = 1 - self._display_mode
                        self._last_toggle = current_time
                else:
                    # 如果类型不对，重置
                    self._last_toggle = current_time

                time.sleep(LCD_CONFIG["refresh_rate"])

            except Exception as e:
                logger.error(f"LCD refresh error: {e}")
                self._last_toggle = time.time()  # 重置
                time.sleep(1)

    def update_message(self, message: str):
        """
        更新LCD显示消息（兼容rasp_integration.py调用）

        Args:
            message: 要显示的消息（第一行）
        """
        self.write_string(message, 1)
        self.write_string("", 2)  # 清空第二行

    def display_status(self, status: str, message: str = ""):
        """
        显示状态信息

        Args:
            status: 状态文本（第一行）
            message: 详细信息（第二行）
        """
        self.write_string(status, 1)
        if message:
            self.write_string(message, 2)

    def display_data(
        self,
        line1: str = "",
        line2: str = "",
        bg: float = 0.0,
        insulin: float = 0.0,
        basal: float = 0.0,
        bolus: float = 0.0,
    ):
        """
        显示血糖和胰岛素数据

        Args:
            line1: 第一行文本（如果提供，优先使用）
            line2: 第二行文本（如果提供，优先使用）
            bg: 血糖值 (mg/dL)
            insulin: 总胰岛素 (U)
            basal: 基础率 (U)
            bolus: 餐时大剂量 (U)
        """
        # 如果提供了line1和line2，直接显示
        if line1 or line2:
            if line1:
                self.write_string(line1, 1)
            if line2:
                self.write_string(line2, 2)
            return

        # 否则使用原有的数据显示逻辑
        if self._display_mode == 0:
            # 模式0: 时间 + 总胰岛素/血糖
            line1 = datetime.now().strftime("%H:%M:%S")
            line2 = f"BG:{bg:>5.1f} I:{insulin:>4.2f}"
        else:
            # 模式1: 基础率和餐时剂量
            line1 = f"Basal: {basal:>6.3f}U"
            line2 = f"Bolus: {bolus:>6.3f}U"

        self.write_string(line1, 1)
        self.write_string(line2, 2)

    def shutdown(self):
        """关闭LCD（兼容rasp_integration.py调用）"""
        self.stop()

    def get_lines(self) -> tuple:
        """获取当前显示内容"""
        with self._display_lock:
            return (self._line1, self._line2)


# 测试代码
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 创建LCD控制器（仿真模式）
    lcd = LCD1602(simulation_mode=True)

    if not lcd.start():
        print("Failed to start LCD")
        sys.exit(1)

    print("LCD started. Testing display...")

    try:
        # 测试状态显示
        lcd.display_status("System Ready", "Waiting...")
        time.sleep(3)

        # 测试数据显示
        for i in range(10):
            bg = 110.0 + i * 5
            insulin = 1.0 + i * 0.2
            basal = 0.8
            bolus = 0.2 + i * 0.2

            lcd.display_data(bg=bg, insulin=insulin, basal=basal, bolus=bolus)

            line1, line2 = lcd.get_lines()
            print(f"Display: [{line1}] [{line2}]")

            time.sleep(2)

        print("\nTest complete. Press Ctrl+C to stop...")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping LCD...")
        lcd.stop()
