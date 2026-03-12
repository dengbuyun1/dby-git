import time

from RPi import GPIO

from config_module import STEP_PIN, DIR_PIN, Plus_Button, Decr_Button
import motor_module as motor


def manual_control() -> None:
    """Manual override for the stepper motor using local buttons."""

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DIR_PIN, GPIO.OUT)
    GPIO.setup(STEP_PIN, GPIO.OUT)
    GPIO.setup(Plus_Button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(Decr_Button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    pwm = GPIO.PWM(STEP_PIN, 5000)
    pwm.start(0)

    motor.set_manual_mode(True)

    try:
        while motor.get_manual_signal():
            direction_pressed = GPIO.input(Plus_Button) == GPIO.LOW
            fire_pressed = GPIO.input(Decr_Button) == GPIO.HIGH

            GPIO.output(DIR_PIN, GPIO.LOW if direction_pressed else GPIO.HIGH)
            pwm.ChangeDutyCycle(50 if fire_pressed else 0)

            time.sleep(0.01)
    finally:
        pwm.stop()
        GPIO.cleanup()
        motor.set_manual_mode(False)


if __name__ == "__main__":
    try:
        manual_control()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print("退出手动控制")
