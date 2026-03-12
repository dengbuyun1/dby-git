"""
蓝牙模块 - 性能优化版

改进点:
1. Socket 超时设置
2. 缓冲区优化
3. 错误重试机制
4. 连接保活
5. 性能监控
"""

import bluetooth
import time
from datetime import datetime
import threading
import struct

# 导入 IOB/COB 模块
import iob_cob_module as iob_cob

# 全局变量
insulin = 0.0
basal_value = 0.0
bolus_value = 0.0
insulin_action = False
last_data_time = None
simulation_running = False
data_str = ""
latest_bg = 0.0
latest_cgm = 0.0
latest_cho = 0.0
latest_iob = 0.0
latest_cob = 0.0

# 性能监控
packet_count = 0
total_latency = 0.0
max_latency = 0.0
min_latency = float("inf")

TARGET_BG = 110.0
BASAL_BASE = 0.8
KP = 0.01
CARB_RATIO = 12.0
CORRECTION_FACTOR = 50.0
IOB_SENSITIVITY = 0.3
COB_BOOST = 0.1

# 性能优化参数
SOCKET_TIMEOUT = 5.0  # 5秒超时
KEEPALIVE_INTERVAL = 30  # 30秒发送一次心跳
MAX_RETRY = 3  # 最大重试次数


def calculate_insulin(bg: float, cgm: float, cho: float) -> tuple[float, float, float]:
    """计算胰岛素剂量 (考虑 IOB/COB)"""
    current_iob, current_cob = iob_cob.get_iob_cob_simple()

    error = bg - TARGET_BG
    basal = max(0.0, BASAL_BASE + KP * error)
    correction = max(0.0, error / CORRECTION_FACTOR)

    iob_suppression = current_iob * IOB_SENSITIVITY
    cob_enhancement = current_cob * COB_BOOST / CARB_RATIO

    bolus_base = cho / CARB_RATIO + correction
    bolus = max(0.0, bolus_base - iob_suppression + cob_enhancement)

    total = basal + bolus
    return total, basal, bolus


def get_insulin():
    global insulin
    return insulin


def get_data_str():
    global data_str
    return data_str


def get_insulin_action():
    global insulin_action
    return insulin_action


def set_insulin_action(value):
    global insulin_action
    insulin_action = value


def get_last_data_time():
    global last_data_time
    return last_data_time


def get_simulation_running():
    global simulation_running
    return simulation_running


def get_basal():
    global basal_value
    return basal_value


def get_bolus():
    global bolus_value
    return bolus_value


def get_latest_readings():
    return latest_bg, latest_cgm, latest_cho


def get_iob_cob():
    return latest_iob, latest_cob


def get_performance_stats():
    """获取性能统计"""
    global packet_count, total_latency, max_latency, min_latency
    if packet_count == 0:
        return {"count": 0, "avg_latency": 0, "max_latency": 0, "min_latency": 0}

    return {
        "count": packet_count,
        "avg_latency": total_latency / packet_count * 1000,  # ms
        "max_latency": max_latency * 1000,
        "min_latency": min_latency * 1000 if min_latency != float("inf") else 0,
    }


def reset_performance_stats():
    """重置性能统计"""
    global packet_count, total_latency, max_latency, min_latency
    packet_count = 0
    total_latency = 0.0
    max_latency = 0.0
    min_latency = float("inf")


def handle_data(input_data_str, db_connection, save_func):
    """处理接收到的数据 (性能优化版)"""
    global insulin, basal_value, bolus_value, insulin_action, last_data_time
    global simulation_running, data_str, latest_bg, latest_cgm, latest_cho
    global latest_iob, latest_cob
    global packet_count, total_latency, max_latency, min_latency

    start_time = time.perf_counter()

    try:
        data_str = input_data_str

        if input_data_str == "STOP_SIMULATION":
            print("收到仿真停止信号")
            simulation_running = False
            insulin_action = False
            insulin = 0.0
            basal_value = 0.0
            bolus_value = 0.0
            last_data_time = None
            latest_bg = latest_cgm = latest_cho = 0.0
            latest_iob = latest_cob = 0.0
            iob_cob.clear_all_history()
            reset_performance_stats()
            return

        parts = input_data_str.split(",")
        if len(parts) < 5:
            print(f"数据格式错误: {input_data_str}")
            return

        vpname = parts[0]
        vtime_str = parts[1]
        bg = float(parts[2])
        cgm = float(parts[3])
        cho = float(parts[4])

        latest_bg, latest_cgm, latest_cho = bg, cgm, cho

        try:
            last_data_time = datetime.fromisoformat(vtime_str)
        except:
            last_data_time = datetime.now()

        if cho > 0:
            iob_cob.add_carb_intake(last_data_time, cho)

        insulin_value, basal, bolus = calculate_insulin(bg, cgm, cho)

        insulin = insulin_value
        basal_value = basal
        bolus_value = bolus
        insulin_action = insulin_value > 0

        if insulin_value > 0:
            iob_cob.add_insulin_dose(last_data_time, basal, bolus)

        latest_iob, latest_cob = iob_cob.get_iob_cob_simple(last_data_time)

        if db_connection:
            save_func(db_connection, vpname, vtime_str, cgm, cho, basal, bolus, insulin)

        data_str = input_data_str
        simulation_running = True

        # 性能统计
        latency = time.perf_counter() - start_time
        packet_count += 1
        total_latency += latency
        max_latency = max(max_latency, latency)
        min_latency = min(min_latency, latency)

        # 每100个包打印一次性能
        if packet_count % 100 == 0:
            stats = get_performance_stats()
            print(
                f"\n[性能统计] 包数:{stats['count']} "
                f"平均延迟:{stats['avg_latency']:.2f}ms "
                f"最大:{stats['max_latency']:.2f}ms "
                f"最小:{stats['min_latency']:.2f}ms\n"
            )

        # 常规日志 (每10个包打印一次,减少输出)
        if packet_count % 10 == 0:
            print(
                f"[{last_data_time:%H:%M:%S}] BG:{bg:.1f} CGM:{cgm:.1f} CHO:{cho:.1f}g "
                f"-> I:{insulin:.3f}U | IOB:{latest_iob:.3f}U COB:{latest_cob:.1f}g "
                f"({latency*1000:.1f}ms)"
            )

    except Exception as e:
        print(f"数据处理错误: {e}")


def bluetooth_server_optimized(db_connection, save_func):
    """蓝牙服务器 - 性能优化版"""
    global insulin

    retry_count = 0

    while True:
        try:
            server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

            # 优化1: Socket 选项
            server_socket.setsockopt(bluetooth.SOL_RFCOMM, bluetooth.RFCOMM_LM, 0)

            port = 2
            server_socket.bind(("", port))
            server_socket.listen(1)

            print(f"等待电脑连接... (端口 {port})")

            client_socket, address = server_socket.accept()
            print(f"从地址 {address} 接受了连接")

            # 优化2: 设置超时
            client_socket.settimeout(SOCKET_TIMEOUT)

            # 重置重试计数
            retry_count = 0

            # 心跳检测
            last_keepalive = time.time()

            while True:
                try:
                    # 优化3: 非阻塞读取
                    data = client_socket.recv(1024)

                    if not data:
                        print("接收到空数据,连接可能已断开")
                        break

                    input_data_str = data.decode("utf-8").strip()

                    # 处理数据
                    handle_data(input_data_str, db_connection, save_func)

                    # 发送响应
                    if input_data_str == "STOP_SIMULATION":
                        response_data = "0,0,0\n"
                    else:
                        response_data = (
                            f"{insulin:.4f},{basal_value:.4f},{bolus_value:.4f}\n"
                        )

                    # 优化4: 立即发送
                    client_socket.send(response_data.encode())

                    # 更新心跳时间
                    last_keepalive = time.time()

                except bluetooth.BluetoothError as e:
                    if "timed out" in str(e).lower():
                        # 超时不是严重错误,检查心跳
                        if time.time() - last_keepalive > KEEPALIVE_INTERVAL:
                            print("心跳超时,连接可能已断开")
                            break
                        continue
                    else:
                        print(f"蓝牙错误: {e}")
                        break
                except Exception as e:
                    print(f"通信错误: {e}")
                    break

        except bluetooth.BluetoothError as e:
            print(f"蓝牙连接错误: {e}")
            retry_count += 1

            if retry_count < MAX_RETRY:
                wait_time = min(2**retry_count, 10)  # 指数退避,最多10秒
                print(f"重试 {retry_count}/{MAX_RETRY},等待 {wait_time}秒...")
                time.sleep(wait_time)
            else:
                print(f"达到最大重试次数,等待60秒后重启...")
                time.sleep(60)
                retry_count = 0

        except Exception as e:
            print(f"未知错误: {e}")
            time.sleep(5)

        finally:
            try:
                client_socket.close()
                server_socket.close()
            except:
                pass
            print("蓝牙连接已关闭,准备重新监听...\n")


def start_bluetooth_server(db_connection, save_func):
    """启动蓝牙服务线程"""
    bluetooth_thread = threading.Thread(
        target=bluetooth_server_optimized, args=(db_connection, save_func)
    )
    bluetooth_thread.daemon = True
    bluetooth_thread.start()
    return bluetooth_thread
