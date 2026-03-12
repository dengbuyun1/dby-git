import RPi.GPIO as GPIO
import time
import threading
from datetime import datetime

# 导入自定义模块
import database_module as db
import bluetooth_module as bt
import motor_module as motor
from manual_control import manual_control


def main():
    try:
        # 连接数据库
        db_connection = db.connect_mysql()
        # 设置GPIO和PWM
        pwm = motor.setup_gpio()
        # 启动蓝牙服务线程
        bluetooth_thread = bt.start_bluetooth_server(db_connection, db.save_to_database)
        # 手动
        # manual_control()
        # 启动电机控制主循环
        motor.motor_control_loop(pwm, bt)

    except KeyboardInterrupt:
        print("程序中断")
    except Exception as e:
        print(f"主程序错误: {e}")
    finally:
        if "db_connection" in locals() and db_connection:
            db_connection.close()
        if "pwm" in locals():
            try:
                pwm.stop()
                GPIO.cleanup()
            except:
                pass
        print("程序结束")


if __name__ == "__main__":
    main()
