import RPi.GPIO as GPIO
import time
from datetime import datetime
from typing import Tuple

from config_module import (
    CONCENTRATION,
    A,
    STEP_DISTANCE,
    TIME_STEP,
    STEP_PIN,
    DIR_PIN,
    Plus_Button,
    Decr_Button,
)
import other_module as peripherals


_manual_mode = False


def setup_gpio():
    """设置步进电机相关的 GPIO 引脚."""

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(STEP_PIN, GPIO.OUT)
    GPIO.setup(DIR_PIN, GPIO.OUT)
    GPIO.setup(Plus_Button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(Decr_Button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.output(DIR_PIN, GPIO.HIGH)
    pwm = GPIO.PWM(STEP_PIN, 100)
    print(f"PWM 初始化成功，STEP_PIN: {STEP_PIN}")
    return pwm


def set_manual_mode(state: bool) -> None:
    global _manual_mode
    _manual_mode = state


def get_manual_signal() -> bool:
    return _manual_mode


def _calculate_steps(insulin_units: float) -> int:
    distance_mm = insulin_units / CONCENTRATION * 1000 / A
    total_steps = distance_mm / STEP_DISTANCE
    return max(0, int(round(total_steps)))


def _update_display(
    timestamp: datetime,
    insulin: float,
    basal: float,
    bolus: float,
    iob: float = 0.0,
    cob: float = 0.0,
) -> None:
    """更新 LCD 显示 (增强版: 显示 IOB/COB)"""
    peripherals.lcd_display_string(f"{timestamp:%H:%M:%S}", 1)
    # 第二行轮换显示: I/B/L 或 IOB/COB
    import time

    cycle = int(time.time()) % 4  # 每秒切换
    if cycle < 2:
        peripherals.lcd_display_string(
            f"I:{insulin:>4.1f} B:{basal:>3.1f} {bolus:>3.1f}", 2
        )
    else:
        peripherals.lcd_display_string(f"IOB:{iob:>4.2f} COB:{cob:>3.0f}", 2)


def motor_control_loop(pwm, bt_module) -> None:
    peripherals.lcd_gpio_setup()
    set_manual_mode(False)
    pwm.start(0)

    try:
        while True:
            simulation_running = bt_module.get_simulation_running()

            if not simulation_running:
                set_manual_mode(True)
                peripherals.set_led_color("red")
                peripherals.lcd_display_string("等待仿真...", 1)
                peripherals.lcd_display_string("Manual Ready", 2)
                pwm.ChangeDutyCycle(0)
                time.sleep(0.2)
                continue

            set_manual_mode(False)
            insulin = bt_module.get_insulin()
            basal = bt_module.get_basal()
            bolus = bt_module.get_bolus()
            iob, cob = bt_module.get_iob_cob()  # 获取 IOB/COB
            last_data_time = bt_module.get_last_data_time() or datetime.now()

            total_steps = _calculate_steps(insulin)

            if total_steps > 0:
                frequency = min(max(total_steps / TIME_STEP, 1), 5000)
                pwm.ChangeFrequency(frequency)
                pwm.ChangeDutyCycle(50)
                peripherals.set_led_color("green")
            else:
                pwm.ChangeDutyCycle(0)
                peripherals.set_led_color("blue")

            _update_display(
                last_data_time, insulin, basal, bolus, iob, cob
            )  # 传递 IOB/COB

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("电机控制中断")
    except Exception as exc:
        print(f"电机控制循环错误: {exc}")
    finally:
        try:
            pwm.stop()
        except Exception:
            pass
        peripherals.cleanup()
        GPIO.cleanup()
