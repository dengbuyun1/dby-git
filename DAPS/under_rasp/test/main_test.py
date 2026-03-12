"""
树莓派TCP测试主程序

功能：
1. 启动TCP服务器接收PC数据
2. 显示接收到的数据
3. 测试胰岛素计算
4. 可选：控制GPIO（如果在真实树莓派上运行）

使用方法：
    python3 main_test.py
"""

import time
import sys
from datetime import datetime

# 导入TCP模块
try:
    from tcp_module import create_tcp_server
except ImportError:
    print("错误: 找不到 tcp_module.py")
    print("请确保 tcp_module.py 在同一目录下")
    sys.exit(1)

# 尝试导入GPIO（仅在真实树莓派上）
try:
    import RPi.GPIO as GPIO

    HAS_GPIO = True
    print("✓ 检测到树莓派GPIO")
except ImportError:
    HAS_GPIO = False
    print("○ 未检测到GPIO（运行在PC上）")


def print_header():
    """打印程序头部"""
    print("\n" + "=" * 60)
    print("  树莓派TCP测试程序 - 血糖监控系统")
    print("=" * 60)
    print(f"  启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  运行环境: {'树莓派 (GPIO可用)' if HAS_GPIO else 'PC (模拟模式)'}")
    print("=" * 60 + "\n")


def print_data_table(data):
    """以表格形式打印数据"""
    print("\n" + "-" * 60)
    print(f"  {'项目':<15} {'值':<20} {'单位':<10}")
    print("-" * 60)
    print(f"  {'患者姓名':<15} {data['pname']:<20}")
    print(f"  {'时间戳':<15} {data['time'][:19]:<20}")
    print(f"  {'血糖 (BG)':<15} {data['bg']:<20.2f} {'mg/dL':<10}")
    print(f"  {'CGM':<15} {data['cgm']:<20.2f} {'mg/dL':<10}")
    print(f"  {'碳水化合物':<15} {data['cho']:<20.2f} {'g':<10}")
    print("-" * 60)
    print(f"  {'总胰岛素':<15} {data['insulin']:<20.4f} {'U':<10}")
    print(f"  {'基础胰岛素':<15} {data['basal']:<20.4f} {'U':<10}")
    print(f"  {'大剂量':<15} {data['bolus']:<20.4f} {'U':<10}")
    print("-" * 60 + "\n")


def setup_gpio():
    """设置GPIO（仅在树莓派上）"""
    if not HAS_GPIO:
        return

    try:
        GPIO.setmode(GPIO.BCM)
        # 示例：使用LED指示状态
        # LED_PIN = 18
        # GPIO.setup(LED_PIN, GPIO.OUT)
        print("✓ GPIO初始化成功")
    except Exception as e:
        print(f"✗ GPIO初始化失败: {e}")


def cleanup_gpio():
    """清理GPIO"""
    if HAS_GPIO:
        try:
            GPIO.cleanup()
            print("✓ GPIO清理完成")
        except:
            pass


def main():
    """主函数"""
    # 打印头部
    print_header()

    # 初始化GPIO
    setup_gpio()

    # 获取配置
    print("TCP服务器配置:")
    print("  监听地址: 0.0.0.0 (所有网络接口)")
    print("  监听端口: 5000")

    # 提示获取IP地址
    if HAS_GPIO:
        print("\n提示: 在树莓派终端运行 'hostname -I' 查看IP地址")

    print("\n正在启动TCP服务器...\n")

    # 创建并启动TCP服务器
    try:
        server = create_tcp_server(host="0.0.0.0", port=5000)
        print("✓ TCP服务器启动成功\n")
    except Exception as e:
        print(f"✗ TCP服务器启动失败: {e}")
        cleanup_gpio()
        return

    # 显示使用说明
    print("使用说明:")
    print("  1. 在PC上的 simulator.py 中设置树莓派IP地址")
    print("  2. 启动PC端的仿真程序")
    print("  3. 在网页上点击'开始仿真'")
    print("  4. 观察下方的数据接收情况")
    print("\n按 Ctrl+C 停止程序\n")
    print("=" * 60)

    # 状态变量
    last_data_time = None
    data_count = 0

    try:
        # 主循环
        while True:
            time.sleep(2)  # 每2秒检查一次

            # 获取最新数据
            data = server.get_latest_data()

            # 检查是否有新数据
            if data["last_update"] and data["last_update"] != last_data_time:
                last_data_time = data["last_update"]
                data_count += 1

                # 打印数据
                print(f"\n【数据 #{data_count}】 {datetime.now().strftime('%H:%M:%S')}")
                print_data_table(data)

                # 在树莓派上可以控制LED闪烁等
                # if HAS_GPIO:
                #     GPIO.output(LED_PIN, GPIO.HIGH)
                #     time.sleep(0.1)
                #     GPIO.output(LED_PIN, GPIO.LOW)

            else:
                # 检查是否正在接收数据
                if server.is_receiving_data():
                    # 正在接收，但本次循环没有新数据
                    pass
                else:
                    # 长时间没数据
                    if data_count > 0:
                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] ⏸ 等待数据... (已接收 {data_count} 条)"
                        )

    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("正在停止程序...")
        print("=" * 60)

    finally:
        # 停止服务器
        print("\n正在关闭TCP服务器...")
        server.stop()

        # 清理GPIO
        cleanup_gpio()

        # 显示统计
        print(f"\n统计信息:")
        print(f"  总接收数据: {data_count} 条")
        print(f"\n程序已退出")


if __name__ == "__main__":
    main()
