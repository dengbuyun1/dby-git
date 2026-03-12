"""
简化的TCP服务器模块 - 用于树莓派接收PC仿真数据

功能：
1. 监听TCP连接（默认端口5000）
2. 接收格式：pname,time,bg,cgm,cho
3. 计算胰岛素剂量（基础算法）
4. 返回格式：insulin,basal,bolus
"""

import socket
import threading
import time
from datetime import datetime


class TCPServer:
    """TCP服务器类"""

    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.thread = None

        # 数据存储
        self.latest_data = {
            "pname": "",
            "time": "",
            "bg": 0.0,
            "cgm": 0.0,
            "cho": 0.0,
            "insulin": 0.0,
            "basal": 0.0,
            "bolus": 0.0,
            "last_update": None,
        }

        # 控制参数（可调整）
        self.TARGET_BG = 110.0  # 目标血糖
        self.BASAL_BASE = 0.8  # 基础胰岛素
        self.KP = 0.01  # 比例系数
        self.CARB_RATIO = 12.0  # 碳水化合物比率
        self.CORRECTION_FACTOR = 50.0  # 校正因子

    def calculate_insulin(self, bg, cgm, cho):
        """
        计算胰岛素剂量

        参数：
            bg: 血糖值
            cgm: CGM值
            cho: 碳水化合物

        返回：
            (insulin, basal, bolus) 元组
        """
        # 基础胰岛素
        basal = self.BASAL_BASE

        # 根据血糖偏差调整
        bg_error = cgm - self.TARGET_BG
        correction = bg_error / self.CORRECTION_FACTOR

        # 餐食补偿
        meal_bolus = cho / self.CARB_RATIO if cho > 0 else 0.0

        # 总bolus = 校正 + 餐食
        bolus = max(0.0, correction + meal_bolus)

        # 总胰岛素
        insulin = basal + bolus

        return insulin, basal, bolus

    def parse_data(self, data_str):
        """
        解析接收到的数据

        格式：pname,time,bg,cgm,cho
        """
        try:
            parts = data_str.strip().split(",")
            if len(parts) != 5:
                return None

            pname = parts[0]
            time_str = parts[1]
            bg = float(parts[2])
            cgm = float(parts[3])
            cho = float(parts[4])

            return {"pname": pname, "time": time_str, "bg": bg, "cgm": cgm, "cho": cho}
        except Exception as e:
            print(f"解析数据失败: {e}")
            return None

    def handle_client(self, client_socket, addr):
        """处理客户端连接"""
        print(f"✓ 客户端连接: {addr}")

        try:
            buffer = ""
            while self.running:
                # 接收数据
                data = client_socket.recv(1024).decode("utf-8")
                if not data:
                    break

                buffer += data

                # 处理完整的消息（以换行符分隔）
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    # 解析数据
                    parsed = self.parse_data(line)
                    if not parsed:
                        print(f"✗ 无效数据: {line}")
                        continue

                    # 计算胰岛素
                    insulin, basal, bolus = self.calculate_insulin(
                        parsed["bg"], parsed["cgm"], parsed["cho"]
                    )

                    # 更新最新数据
                    self.latest_data.update(parsed)
                    self.latest_data["insulin"] = insulin
                    self.latest_data["basal"] = basal
                    self.latest_data["bolus"] = bolus
                    self.latest_data["last_update"] = datetime.now()

                    # 打印接收到的数据
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 接收数据:")
                    print(f"  患者: {parsed['pname']}")
                    print(f"  血糖: {parsed['bg']:.1f} mg/dL")
                    print(f"  CGM: {parsed['cgm']:.1f} mg/dL")
                    print(f"  碳水: {parsed['cho']:.1f} g")
                    print(
                        f"  → 胰岛素: {insulin:.4f} U (基础: {basal:.4f}, 大剂量: {bolus:.4f})"
                    )

                    # 发送响应
                    response = f"{insulin:.4f},{basal:.4f},{bolus:.4f}\n"
                    client_socket.send(response.encode("utf-8"))

        except Exception as e:
            print(f"✗ 处理客户端出错: {e}")
        finally:
            client_socket.close()
            print(f"✗ 客户端断开: {addr}")

    def run_server(self):
        """运行TCP服务器（在线程中）"""
        try:
            # 创建socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0)  # 1秒超时，用于检查running标志

            print(f"✓ TCP服务器启动成功")
            print(f"  监听地址: {self.host}:{self.port}")
            print(f"  等待PC连接...")

            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    # 为每个客户端创建新线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True,
                    )
                    client_thread.start()
                except socket.timeout:
                    continue  # 超时后继续检查running标志
                except Exception as e:
                    if self.running:
                        print(f"✗ 接受连接出错: {e}")

        except Exception as e:
            print(f"✗ TCP服务器启动失败: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            print("✗ TCP服务器已关闭")

    def start(self):
        """启动TCP服务器"""
        if self.running:
            print("服务器已在运行")
            return

        self.running = True
        self.thread = threading.Thread(target=self.run_server, daemon=True)
        self.thread.start()

        # 等待服务器启动
        time.sleep(0.5)

    def stop(self):
        """停止TCP服务器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)

    def get_latest_data(self):
        """获取最新接收的数据"""
        return self.latest_data.copy()

    def is_receiving_data(self):
        """检查是否正在接收数据"""
        if not self.latest_data["last_update"]:
            return False

        # 如果超过5秒没收到数据，认为断开
        elapsed = (datetime.now() - self.latest_data["last_update"]).total_seconds()
        return elapsed < 5.0


# 便捷函数
def create_tcp_server(host="0.0.0.0", port=5000):
    """创建并启动TCP服务器"""
    server = TCPServer(host, port)
    server.start()
    return server


# 测试代码
if __name__ == "__main__":
    print("=" * 50)
    print("TCP服务器测试程序")
    print("=" * 50)

    # 创建并启动服务器
    server = create_tcp_server()

    print("\n按 Ctrl+C 停止服务器\n")

    try:
        # 每5秒打印一次状态
        while True:
            time.sleep(5)
            if server.is_receiving_data():
                data = server.get_latest_data()
                print(
                    f"\n[状态] 正在接收数据 - BG: {data['bg']:.1f}, CGM: {data['cgm']:.1f}"
                )
            else:
                print("\n[状态] 等待数据...")
    except KeyboardInterrupt:
        print("\n\n正在停止服务器...")
        server.stop()
        print("服务器已停止")
