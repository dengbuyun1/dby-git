# Utilities for LCD1602 display, RGB LED, and buttons on Raspberry Pi using gpiozero.
from __future__ import annotations

import logging
import threading
import time
from typing import TYPE_CHECKING, Callable, Optional, Sequence

from gpiozero import Button, RGBLED

try:
    from smbus2 import SMBus  # type: ignore
except ImportError:  # SMBus is optional for development on non-Pi hosts
    SMBus = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from smbus2 import SMBus as SMBusType  # type: ignore
else:
    SMBusType = object  # fallback placeholder for type hints

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GPIO assignments
# ---------------------------------------------------------------------------
LED_RED_PIN = 18
LED_GREEN_PIN = 19
LED_BLUE_PIN = 20

PRESSURE_BUTTON_PIN = 6  # 压力按钮
NO_BUTTON_PIN = 5  # 常开按钮

LCD_I2C_ADDRESS = 0x27
I2C_BUS_ID = 1


# ---------------------------------------------------------------------------
# Global state expected by other modules
# ---------------------------------------------------------------------------
manual = False  # Imported by motor_module for manual mode flags

rgb_led = RGBLED(LED_RED_PIN, LED_GREEN_PIN, LED_BLUE_PIN)
pressure_button = Button(PRESSURE_BUTTON_PIN, pull_up=False, bounce_time=0.05)
normally_open_button = Button(NO_BUTTON_PIN, pull_up=True, bounce_time=0.05)


# ---------------------------------------------------------------------------
# LCD1602 driver (PCF8574 I2C backpack)
# ---------------------------------------------------------------------------
LCD_CMD = 0x00
LCD_CHR = 0x01
LCD_BACKLIGHT = 0x08
ENABLE = 0x04

E_PULSE = 0.0005
E_DELAY = 0.0005


class LCD1602:
    """Minimal 1602 LCD driver for the typical PCF8574 I2C backpack."""

    def __init__(self, address: int, bus_id: int) -> None:
        self.address = address
        self.bus_id = bus_id
        self._bus: Optional[SMBusType] = None
        self._lock = threading.Lock()
        self._initialised = False

        if SMBus is None:
            logger.warning("smbus2 not installed; LCD output disabled")
        else:
            try:
                self._bus = SMBus(self.bus_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("无法打开I2C总线 %s: %s", self.bus_id, exc)
                self._bus = None

    # ------------------------------------------------------------------
    # Low-level helpers
    # ------------------------------------------------------------------
    def _write_byte(self, data: int) -> None:
        if not self._bus:
            return
        with self._lock:
            self._bus.write_byte(self.address, data)

    def _toggle_enable(self, data: int) -> None:
        time.sleep(E_DELAY)
        self._write_byte(data | ENABLE)
        time.sleep(E_PULSE)
        self._write_byte(data & ~ENABLE)
        time.sleep(E_DELAY)

    def _send_byte(self, bits: int, mode: int) -> None:
        high_bits = mode | (bits & 0xF0) | LCD_BACKLIGHT
        low_bits = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT

        self._write_byte(high_bits)
        self._toggle_enable(high_bits)
        self._write_byte(low_bits)
        self._toggle_enable(low_bits)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def init_display(self) -> None:
        if not self._bus:
            return
        self._send_byte(0x33, LCD_CMD)  # Initialise
        self._send_byte(0x32, LCD_CMD)  # Set to 4-bit mode
        self._send_byte(0x06, LCD_CMD)  # Cursor move direction
        self._send_byte(0x0C, LCD_CMD)  # Turn cursor off
        self._send_byte(0x28, LCD_CMD)  # 2 line display
        self._send_byte(0x01, LCD_CMD)  # Clear display
        time.sleep(E_DELAY)
        self._initialised = True

    def clear(self) -> None:
        if not self._bus:
            return
        self._send_byte(0x01, LCD_CMD)
        time.sleep(E_DELAY)

    def display_string(self, message: str, line: int = 1) -> None:
        if not self._bus:
            return
        if not self._initialised:
            self.init_display()

        line_addresses = {1: 0x80, 2: 0xC0, 3: 0x94, 4: 0xD4}
        address = line_addresses.get(line, 0x80)
        self._send_byte(address, LCD_CMD)

        message = message.ljust(16)[:16]
        for char in message:
            self._send_byte(ord(char), LCD_CHR)

    def cleanup(self) -> None:
        if self._bus:
            try:
                self.clear()
                self._bus.close()
            except Exception:  # noqa: BLE001
                pass
        self._bus = None
        self._initialised = False


class DummyLCD:
    """Fallback LCD driver used when smbus is unavailable."""

    def init_display(self) -> None:  # pragma: no cover - trivial fallback
        logger.debug("DummyLCD.init_display called")

    def clear(self) -> None:  # pragma: no cover
        logger.debug("DummyLCD.clear called")

    def display_string(self, message: str, line: int = 1) -> None:  # pragma: no cover
        logger.info("LCD[%s]: %s", line, message)

    def cleanup(self) -> None:  # pragma: no cover
        logger.debug("DummyLCD.cleanup called")


lcd = LCD1602(LCD_I2C_ADDRESS, I2C_BUS_ID) if SMBus else DummyLCD()


# ---------------------------------------------------------------------------
# Public helpers referenced by other modules (motor_module imports *)
# ---------------------------------------------------------------------------
def lcd_gpio_setup() -> None:
    """Initialise the LCD and reset visual state."""

    lcd.init_display()
    lcd.display_string("Ready", 1)
    rgb_led.off()


def set_contrast(level: int) -> None:
    """Legacy hook for contrast control. Retained for compatibility."""

    logger.debug("set_contrast(%s) called - no-op for I2C backpack", level)
    return None


def lcd_init() -> None:
    lcd.init_display()


def lcd_display_string(text: str, line: int = 1) -> None:
    lcd.display_string(text, line)


def lcd_clear() -> None:
    lcd.clear()


def cleanup() -> None:
    lcd.cleanup()
    rgb_led.close()
    pressure_button.close()
    normally_open_button.close()


# ---------------------------------------------------------------------------
# LED control helpers
# ---------------------------------------------------------------------------
COLOR_MAP = {
    "off": (0, 0, 0),
    "red": (1, 0, 0),
    "green": (0, 1, 0),
    "blue": (0, 0, 1),
    "yellow": (1, 1, 0),
    "cyan": (0, 1, 1),
    "magenta": (1, 0, 1),
    "white": (1, 1, 1),
}


def set_led_color(color: str) -> None:
    """Set LED to a predefined colour name."""

    rgb_led.color = COLOR_MAP.get(color.lower(), (0, 0, 0))


def set_led_rgb(r: float, g: float, b: float) -> None:
    """Set LED using normalised RGB values (0.0 - 1.0)."""

    rgb_led.color = (
        max(0.0, min(1.0, r)),
        max(0.0, min(1.0, g)),
        max(0.0, min(1.0, b)),
    )


def cycle_led_colors(
    colors: Optional[Sequence[str]] = None, interval: float = 1.0
) -> None:
    """Cycle through colour names for a simple status animation."""

    colors = colors or ("red", "green", "blue")
    try:
        for name in colors:
            set_led_color(name)
            time.sleep(max(0.05, interval))
    finally:
        rgb_led.off()


# ---------------------------------------------------------------------------
# Button helper functions
# ---------------------------------------------------------------------------
def bind_pressure_button(
    on_press: Optional[Callable[[], None]] = None,
    on_release: Optional[Callable[[], None]] = None,
) -> None:
    pressure_button.when_pressed = on_press
    pressure_button.when_released = on_release


def bind_no_button(
    on_press: Optional[Callable[[], None]] = None,
    on_release: Optional[Callable[[], None]] = None,
) -> None:
    normally_open_button.when_pressed = on_press
    normally_open_button.when_released = on_release


def pressure_pressed() -> bool:
    return pressure_button.is_pressed


def no_button_pressed() -> bool:
    return normally_open_button.is_pressed


__all__ = [
    "manual",
    "rgb_led",
    "pressure_button",
    "normally_open_button",
    "lcd",
    "lcd_gpio_setup",
    "set_contrast",
    "lcd_init",
    "lcd_display_string",
    "lcd_clear",
    "cleanup",
    "set_led_color",
    "set_led_rgb",
    "cycle_led_colors",
    "bind_pressure_button",
    "bind_no_button",
    "pressure_pressed",
    "no_button_pressed",
]
# lcd-1602，LED，button，
