import bluetooth
import time
from datetime import datetime
import threading

# 导入 IOB/COB 模块
import iob_cob_module as iob_cob

# 全局变量
insulin = 0.0
basal_value = 0.0
bolus_value = 0.0
insulin_action = False
last_data_time = None
simulation_running = False
data_str = ""  # 全局变量,确保已定义
latest_bg = 0.0
latest_cgm = 0.0
latest_cho = 0.0
latest_iob = 0.0  # 新增
latest_cob = 0.0  # 新增

TARGET_BG = 110.0
BASAL_BASE = 0.8
KP = 0.01
CARB_RATIO = 12.0
CORRECTION_FACTOR = 50.0

# IOB/COB 影响系数
IOB_SENSITIVITY = 0.3  # IOB 对胰岛素剂量的抑制系数
COB_BOOST = 0.1  # COB 对胰岛素剂量的增强系数


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
    # 获取当前 IOB 和 COB
    current_iob, current_cob = iob_cob.get_iob_cob_simple()

    # 基础计算
    error = bg - TARGET_BG
    basal = max(0.0, BASAL_BASE + KP * error)
    correction = max(0.0, error / CORRECTION_FACTOR)

    # IOB 抑制: 体内已有胰岛素,减少新增剂量
    iob_suppression = current_iob * IOB_SENSITIVITY

    # COB 增强: 未吸收碳水,适当增加剂量
    cob_enhancement = current_cob * COB_BOOST / CARB_RATIO

    # 计算 bolus (考虑 IOB/COB)
    bolus_base = cho / CARB_RATIO + correction
    bolus = max(0.0, bolus_base - iob_suppression + cob_enhancement)

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
        data_str = input_data_str  # 使用参数 input_data_str 更新全局变量 data_str

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
            iob_cob.clear_all_history()
            return

        # 解析数据
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

        # 解析时间
        try:
            last_data_time = datetime.fromisoformat(vtime_str)
        except:
            last_data_time = datetime.now()

        # 记录碳水摄入
        if cho > 0:
            iob_cob.add_carb_intake(last_data_time, cho)

        # 计算胰岛素 (已考虑 IOB/COB)
        insulin_value, basal, bolus = calculate_insulin(bg, cgm, cho)

        insulin = insulin_value
        basal_value = basal
        bolus_value = bolus
        insulin_action = insulin_value > 0

        # 记录胰岛素剂量
        if insulin_value > 0:
            iob_cob.add_insulin_dose(last_data_time, basal, bolus)

        # 更新 IOB/COB
        latest_iob, latest_cob = iob_cob.get_iob_cob_simple(last_data_time)

        # 保存到数据库
        if db_connection:
            save_func(db_connection, vpname, vtime_str, cgm, cho, basal, bolus, insulin)

        data_str = input_data_str
        simulation_running = True

        # 调试输出
        print(
            f"[{last_data_time:%H:%M:%S}] BG:{bg:.1f} CGM:{cgm:.1f} CHO:{cho:.1f}g "
            f"-> I:{insulin:.3f}U (B:{basal:.3f} L:{bolus:.3f}) "
            f"| IOB:{latest_iob:.3f}U COB:{latest_cob:.1f}g"
        )

    except Exception as e:
        print(f"数据处理错误: {e}")


def bluetooth_server(db_connection, save_func):
    """蓝牙服务器线程函数"""
    global insulin

    while True:
        try:
            server_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            port = 2
            server_socket.bind(("", port))
            server_socket.listen(1)
            print("等待电脑连接...")

            client_socket, address = server_socket.accept()
            print(f"从地址 {address} 接受了连接")

            while True:
                try:
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

                except bluetooth.btcommon.BluetoothError as e:
                    print(f"蓝牙错误: {e}")
                    break
                except Exception as e:
                    print(f"其他错误: {e}")
                    break

        except bluetooth.btcommon.BluetoothError as e:
            print(f"蓝牙错误: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"其他错误: {e}")
            time.sleep(1)
        finally:
            try:
                client_socket.close()
                server_socket.close()
            except:
                pass
            print("蓝牙连接已关闭，准备重新监听...")


def start_bluetooth_server(db_connection, save_func):
    """启动蓝牙服务线程"""
    bluetooth_thread = threading.Thread(
        target=bluetooth_server, args=(db_connection, save_func)
    )
    bluetooth_thread.daemon = True
    bluetooth_thread.start()
    return bluetooth_thread
