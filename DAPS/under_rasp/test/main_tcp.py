"""
树莓派主程序 - TCP版本
使用TCP连接替代蓝牙，更简单、更稳定
"""

import time
import os
import sys

# 检查是否在树莓派上运行
try:
    import RPi.GPIO as GPIO

    ON_RASPBERRY_PI = True
except ImportError:
    print("警告: 未检测到RPi.GPIO，使用模拟模式运行（非树莓派环境）")
    ON_RASPBERRY_PI = False

# 导入自定义模块
try:
    import database_module as db
except ImportError:
    print("警告: database_module 未找到，数据库功能将被禁用")
    db = None

# 导入TCP服务器模块
import tcp_server_module as tcp

# 导入电机模块（仅在树莓派上）
if ON_RASPBERRY_PI:
    try:
        import motor_module as motor
    except ImportError:
        print("警告: motor_module 未找到，电机功能将被禁用")
        motor = None
else:
    motor = None


def main():
    """主函数"""
    db_connection = None
    pwm = None
    tcp_thread = None

    try:
        print("=" * 60)
        print("树莓派血糖控制系统 - TCP版本")
        print("=" * 60)

        # 连接数据库（可选）
        if db:
            try:
                db_connection = db.connect_mysql()
                print("✓ 数据库连接成功")
            except Exception as e:
                print(f"✗ 数据库连接失败: {e}")
                db_connection = None
        else:
            print("- 数据库模块未加载，跳过")

        # 设置GPIO和PWM（仅在树莓派上）
        if ON_RASPBERRY_PI and motor:
            try:
                pwm = motor.setup_gpio()
                print("✓ GPIO和PWM初始化成功")
            except Exception as e:
                print(f"✗ GPIO初始化失败: {e}")
                pwm = None
        else:
            print("- 非树莓派环境或电机模块未加载，跳过GPIO设置")

        # 启动TCP服务器线程
        tcp_thread = tcp.start_tcp_server(
            db_connection=db_connection, save_func=db.save_to_database if db else None
        )
        print("✓ TCP服务器线程启动成功")

        print("\n系统就绪，等待PC连接...")
        print("按 Ctrl+C 停止程序\n")

        # 如果有电机模块，启动电机控制循环
        if ON_RASPBERRY_PI and motor and pwm:
            print("启动电机控制循环...")
            motor.motor_control_loop(pwm, tcp)
        else:
            # 否则保持主线程运行
            print("运行在监控模式（无电机控制）...")
            while True:
                time.sleep(1)
                # 显示当前状态
                if tcp.get_simulation_running():
                    bg, cgm, cho = tcp.get_latest_readings()
                    insulin = tcp.get_insulin()
                    basal = tcp.get_basal()
                    bolus = tcp.get_bolus()
                    print(
                        f"\r当前状态: BG={bg:.1f} CGM={cgm:.1f} CHO={cho:.1f}g "
                        f"→ Insulin={insulin:.3f}U (B={basal:.3f} b={bolus:.3f})    ",
                        end="",
                        flush=True,
                    )

    except KeyboardInterrupt:
        print("\n\n收到中断信号，正在关闭...")
    except Exception as e:
        print(f"\n主程序错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # 清理资源
        print("\n正在清理资源...")

        if db_connection and db:
            try:
                db_connection.close()
                print("✓ 数据库连接已关闭")
            except:
                pass

        if ON_RASPBERRY_PI and pwm:
            try:
                pwm.stop()
                GPIO.cleanup()
                print("✓ GPIO已清理")
            except:
                pass

        print("程序结束")


if __name__ == "__main__":
    main()
