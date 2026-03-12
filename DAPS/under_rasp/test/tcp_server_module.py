"""TCP server module for Raspberry Pi to receive simulation data from PC.

This module listens for TCP connections on port 5000 (configurable) and processes
incoming simulation data to calculate insulin doses.
"""

import socket
import time
from datetime import datetime
import threading

# 导入 IOB/COB 模块
try:
    import iob_cob_module as iob_cob

    HAS_IOB_COB = True
except ImportError:
    HAS_IOB_COB = False
    print("警告: iob_cob_module 未找到，将使用基础计算")

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

# 控制参数
TARGET_BG = 110.0
BASAL_BASE = 0.8
KP = 0.01
CARB_RATIO = 12.0
CORRECTION_FACTOR = 50.0

# IOB/COB 影响系数
IOB_SENSITIVITY = 0.3  # IOB 对胰岛素剂量的抑制系数
COB_BOOST = 0.1  # COB 对胰岛素剂量的增强系数

# TCP 配置
TCP_HOST = "0.0.0.0"  # 监听所有网络接口
TCP_PORT = 5000  # 默认端口


def calculate_insulin(bg: float, cgm: float, cho: float) -> tuple[float, float, float]:
    """
    计算胰岛素剂量 (增强版: 考虑 IOB/COB)

    Args:
        bg: 血糖值 (mg/dL)
        cgm: CGM 读数 (mg/dL)
        cho: 碳水摄入 (g)

    Returns:
        (total_insulin, basal, bolus)
    """
    # 基础计算
    error = bg - TARGET_BG
    basal = max(0.0, BASAL_BASE + KP * error)
    correction = max(0.0, error / CORRECTION_FACTOR)

    if HAS_IOB_COB:
        # 获取当前 IOB 和 COB
        current_iob, current_cob = iob_cob.get_iob_cob_simple()

        # IOB 抑制: 体内已有胰岛素，减少新增剂量
        iob_suppression = current_iob * IOB_SENSITIVITY

        # COB 增强: 未吸收碳水，适当增加剂量
        cob_enhancement = current_cob * COB_BOOST / CARB_RATIO

        # 计算 bolus (考虑 IOB/COB)
        bolus_base = cho / CARB_RATIO + correction
        bolus = max(0.0, bolus_base - iob_suppression + cob_enhancement)
    else:
        # 基础计算（无 IOB/COB）
        bolus = max(0.0, cho / CARB_RATIO + correction)

    total = basal + bolus
    return total, basal, bolus


def get_insulin():
    """获取当前胰岛素值"""
    global insulin
    return insulin


def get_data_str():
    """获取当前数据字符串"""
    global data_str
    return data_str


def get_insulin_action():
    """获取胰岛素动作状态"""
    global insulin_action
    return insulin_action


def set_insulin_action(value):
    """设置胰岛素动作状态"""
    global insulin_action
    insulin_action = value


def get_last_data_time():
    """获取最后数据时间"""
    global last_data_time
    return last_data_time


def get_simulation_running():
    """获取仿真运行状态"""
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
    """获取当前 IOB 和 COB"""
    return latest_iob, latest_cob


def handle_data(input_data_str, db_connection, save_func):
    """处理接收到的数据"""
    global insulin, basal_value, bolus_value, insulin_action, last_data_time
    global simulation_running, data_str, latest_bg, latest_cgm, latest_cho
    global latest_iob, latest_cob

    try:
        # 更新全局 data_str
        data_str = input_data_str

        # 检查是否是停止信号
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
            # 清空 IOB/COB 历史
            if HAS_IOB_COB:
                iob_cob.clear_all_history()
            return

        # 解析数据：pname,timestamp,bg,cgm,cho
        parts = input_data_str.split(",")
        if len(parts) < 5:
            print(f"数据格式错误，期望至少5个字段，实际接收: {input_data_str}")
            return

        vpname = parts[0]
        timestamp_str = parts[1]
        bg = float(parts[2])
        cgm = float(parts[3])
        cho = float(parts[4])

        # 更新最新读数
        latest_bg = bg
        latest_cgm = cgm
        latest_cho = cho

        # 计算胰岛素剂量
        insulin, basal_value, bolus_value = calculate_insulin(bg, cgm, cho)

        # 更新 IOB/COB 历史
        if HAS_IOB_COB:
            iob_cob.add_insulin_event(insulin)
            iob_cob.add_carb_event(cho)
            latest_iob, latest_cob = iob_cob.get_iob_cob_simple()

        # 设置胰岛素动作标志
        insulin_action = insulin > 0.1
        simulation_running = True
        last_data_time = datetime.now()

        print(
            f"[{timestamp_str}] BG={bg:.1f}, CGM={cgm:.1f}, CHO={cho:.1f}g → "
            f"Insulin={insulin:.3f}U (Basal={basal_value:.3f}, Bolus={bolus_value:.3f})"
        )

        # 保存到数据库（如果提供了保存函数）
        if save_func and db_connection:
            try:
                save_func(
                    db_connection,
                    vpname,
                    timestamp_str,
                    cgm,
                    cho,
                    basal_value,
                    bolus_value,
                    insulin,
                )
            except Exception as e:
                print(f"保存数据库失败: {e}")

    except ValueError as e:
        print(f"数据解析错误: {e}, 数据: {input_data_str}")
    except Exception as e:
        print(f"数据处理错误: {e}")


def tcp_server(db_connection=None, save_func=None, host=TCP_HOST, port=TCP_PORT):
    """TCP服务器线程函数"""
    global insulin, basal_value, bolus_value

    while True:
        server_socket = None
        client_socket = None
        try:
            # 创建TCP socket
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((host, port))
            server_socket.listen(1)
            print(f"TCP服务器启动，监听 {host}:{port}，等待PC连接...")

            # 接受连接
            client_socket, address = server_socket.accept()
            print(f"从地址 {address} 接受了TCP连接")

            while True:
                try:
                    # 接收数据
                    data = client_socket.recv(1024)
                    if not data:
                        print("接收到空数据，连接可能已断开")
                        break

                    # 处理接收到的数据
                    input_data_str = data.decode("utf-8").strip()
                    print(f"收到数据: {input_data_str}")

                    # 处理数据并更新insulin值
                    handle_data(input_data_str, db_connection, save_func)

                    # 发送响应回客户端（与PC端协议对齐：insulin,basal,bolus）
                    if input_data_str == "STOP_SIMULATION":
                        response_data = "0,0,0\n"
                    else:
                        response_data = (
                            f"{insulin:.4f},{basal_value:.4f},{bolus_value:.4f}\n"
                        )
                    client_socket.send(response_data.encode())

                except socket.error as e:
                    print(f"Socket错误: {e}")
                    break
                except Exception as e:
                    print(f"处理数据时出错: {e}")
                    break

        except socket.error as e:
            print(f"服务器Socket错误: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"服务器其他错误: {e}")
            time.sleep(1)
        finally:
            # 清理连接
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
            if server_socket:
                try:
                    server_socket.close()
                except:
                    pass
            print("TCP连接已关闭，准备重新监听...")
            time.sleep(1)


def start_tcp_server(db_connection=None, save_func=None, host=TCP_HOST, port=TCP_PORT):
    """启动TCP服务线程"""
    tcp_thread = threading.Thread(
        target=tcp_server, args=(db_connection, save_func, host, port), daemon=True
    )
    tcp_thread.start()
    print(f"TCP服务器线程已启动")
    return tcp_thread


# 测试代码
if __name__ == "__main__":
    print("TCP服务器模块测试")
    print("启动TCP服务器...")

    # 启动服务器
    thread = start_tcp_server()

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
