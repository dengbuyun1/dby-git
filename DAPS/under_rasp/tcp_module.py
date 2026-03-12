"""
TCP通信模块 - 与PC端后端建立TCP连接
接收仿真数据并返回控制指令
"""

import socket
import threading
import queue
import time
import logging
import json
from typing import Optional, Callable, Tuple
from datetime import datetime

from config_module import (
    TCP_SERVER_HOST,
    TCP_SERVER_PORT,
    TCP_BUFFER_SIZE,
    TCP_TIMEOUT,
)

logger = logging.getLogger("TCPModule")


class TCPServer:
    """TCP服务器：接收PC端数据并返回控制指令"""

    def __init__(self, host: str = TCP_SERVER_HOST, port: int = TCP_SERVER_PORT):
        self.host = host
        self.port = port
        self._server_socket: Optional[socket.socket] = None
        self._client_socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._data_callback: Optional[Callable] = None

        # 接收到的最新数据
        self._latest_data = {
            "patient_name": "",
            "timestamp": None,
            "bg": 0.0,
            "cgm": 0.0,
            "cho": 0.0,
            "received_count": 0,
            "last_update": None,
        }
        self._data_lock = threading.Lock()

        # 控制指令（将由算法模块设置）
        self._control_output = {
            "insulin": 0.0,
            "basal": 0.0,
            "bolus": 0.0,
        }
        self._output_lock = threading.Lock()

    def start(self, data_callback: Optional[Callable] = None) -> bool:
        """
        启动TCP服务器

        Args:
            data_callback: 数据接收回调函数，接收解析后的数据字典

        Returns:
            是否成功启动
        """
        if self._running:
            logger.warning("TCP server already running")
            return False

        self._data_callback = data_callback
        self._running = True

        # 创建服务器socket
        try:
            self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(1)
            self._server_socket.settimeout(1.0)  # 设置超时以便检查_running标志

            logger.info(f"TCP server listening on {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start TCP server: {e}")
            self._running = False
            return False

        # 启动监听线程
        self._thread = threading.Thread(target=self._server_loop, daemon=True)
        self._thread.start()

        return True

    def stop(self):
        """停止TCP服务器"""
        logger.info("Stopping TCP server...")
        self._running = False

        if self._client_socket:
            try:
                self._client_socket.close()
            except:
                pass

        if self._server_socket:
            try:
                self._server_socket.close()
            except:
                pass

        if self._thread:
            self._thread.join(timeout=2)

        logger.info("TCP server stopped")

    def _server_loop(self):
        """服务器主循环"""
        while self._running:
            try:
                # 等待客户端连接
                logger.info("Waiting for client connection...")
                try:
                    client_socket, client_address = self._server_socket.accept()
                except socket.timeout:
                    continue

                logger.info(f"Client connected from {client_address}")
                self._client_socket = client_socket
                self._client_socket.settimeout(TCP_TIMEOUT)

                # 处理客户端连接
                self._handle_client()

            except Exception as e:
                if self._running:
                    logger.error(f"Server loop error: {e}")
                    time.sleep(1)

        logger.info("Server loop exited")

    def _handle_client(self):
        """处理客户端连接"""
        buffer = ""

        while self._running:
            try:
                # 接收数据
                data = self._client_socket.recv(TCP_BUFFER_SIZE)
                if not data:
                    logger.info("Client disconnected")
                    break

                # 解码并添加到缓冲区
                buffer += data.decode("utf-8")

                # 处理完整的行（以\n分隔）
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if line:
                        self._process_message(line)

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error handling client: {e}")
                break

        # 关闭客户端连接
        try:
            self._client_socket.close()
        except:
            pass
        self._client_socket = None

    def _process_message(self, message: str):
        """
        处理接收到的消息

        消息格式: JSON 或 CSV
        JSON: {"patient_name":..., "timestamp":..., "bg":..., "cgm":..., "cho":..., "controller":...}
        CSV: "patient_name,timestamp,bg,cgm,cho"
        """
        try:
            if message == "STOP_SIMULATION":
                logger.info("Received STOP_SIMULATION signal")
                self._handle_stop_signal()
                response = "0.0000,0.0000,0.0000\n"
            else:
                controller_type = "default"
                parsed_data = {}  # 准备传递给回调的完整数据字典

                # 尝试解析 JSON
                try:
                    data = json.loads(message)
                    parsed_data = data.copy()  # 保留所有原始字段 (包括 kp, ki, kd 等)

                    patient_name = data.get("patient_name", "Unknown")
                    timestamp_str = data.get("timestamp", str(time.time()))
                    bg = float(data.get("bg", 0.0))
                    cgm = float(data.get("cgm", 0.0))
                    cho = float(data.get("cho", 0.0))
                    controller_type = data.get("controller", "default")
                except json.JSONDecodeError:
                    # 回退到 CSV 解析
                    parts = message.split(",")
                    if len(parts) != 5:
                        logger.warning(f"Invalid message format: {message}")
                        return

                    patient_name = parts[0]
                    timestamp_str = parts[1]
                    bg = float(parts[2])
                    cgm = float(parts[3])
                    cho = float(parts[4])

                    parsed_data = {
                        "patient_name": patient_name,
                        "timestamp": timestamp_str,
                        "bg": bg,
                        "cgm": cgm,
                        "cho": cho,
                        "controller": "default",
                    }

                # 解析时间戳（支持Unix时间戳浮点数或ISO格式）
                # ✅ 最终统一转换为float类型的Unix时间戳
                try:
                    # 尝试作为Unix时间戳解析
                    timestamp = float(timestamp_str)
                except ValueError:
                    # 尝试作为ISO格式解析
                    try:
                        dt = datetime.fromisoformat(timestamp_str)
                        timestamp = dt.timestamp()  # 转为float
                    except:
                        timestamp = time.time()  # 使用当前时间

                # 更新数据到 parsed_data，确保格式统一
                parsed_data["patient_name"] = patient_name
                parsed_data["timestamp"] = timestamp
                parsed_data["bg"] = bg
                parsed_data["cgm"] = cgm
                parsed_data["cho"] = cho
                parsed_data["controller"] = controller_type

                # 更新内部状态
                with self._data_lock:
                    self._latest_data["patient_name"] = patient_name
                    self._latest_data["timestamp"] = timestamp  # ✅ 现在是float
                    self._latest_data["bg"] = bg
                    self._latest_data["cgm"] = cgm
                    self._latest_data["cho"] = cho
                    self._latest_data["controller"] = controller_type
                    self._latest_data["received_count"] += 1
                    self._latest_data["last_update"] = datetime.now()

                logger.debug(
                    f"Received: BG={bg:.1f}, CGM={cgm:.1f}, CHO={cho:.1f}, CTRL={controller_type}"
                )

                # 调用回调函数并获取返回值
                hardware_data = {}
                if self._data_callback:
                    # 传递包含所有字段的 parsed_data，而不仅仅是部分字段
                    callback_result = self._data_callback(parsed_data)

                    # 如果回调返回字典，使用返回值更新控制输出
                    if isinstance(callback_result, dict):
                        with self._output_lock:
                            self._control_output["insulin"] = callback_result.get(
                                "insulin", 0.0
                            )
                            self._control_output["basal"] = callback_result.get(
                                "basal", 0.0
                            )
                            self._control_output["bolus"] = callback_result.get(
                                "bolus", 0.0
                            )
                        hardware_data = callback_result.get("hardware", {})

                # 获取控制输出
                with self._output_lock:
                    insulin = self._control_output["insulin"]
                    basal = self._control_output["basal"]
                    bolus = self._control_output["bolus"]

                # 发送响应 (JSON格式)
                response_dict = {
                    "insulin": insulin,
                    "basal": basal,
                    "bolus": bolus,
                    "hardware": hardware_data,
                }
                response = json.dumps(response_dict) + "\n"

            # 发送响应
            if self._client_socket:
                self._client_socket.sendall(response.encode("utf-8"))
                logger.debug(f"Sent response: {response.strip()}")

        except Exception as e:
            logger.error(f"Error processing message '{message}': {e}")

    def _handle_stop_signal(self):
        """处理停止信号"""
        with self._data_lock:
            self._latest_data["patient_name"] = ""
            self._latest_data["timestamp"] = None
            self._latest_data["bg"] = 0.0
            self._latest_data["cgm"] = 0.0
            self._latest_data["cho"] = 0.0

        with self._output_lock:
            self._control_output["insulin"] = 0.0
            self._control_output["basal"] = 0.0
            self._control_output["bolus"] = 0.0

    def get_latest_data(self) -> dict:
        """获取最新接收的数据"""
        with self._data_lock:
            return self._latest_data.copy()

    def set_control_output(self, insulin: float, basal: float, bolus: float):
        """设置控制输出（由算法模块调用）"""
        with self._output_lock:
            self._control_output["insulin"] = insulin
            self._control_output["basal"] = basal
            self._control_output["bolus"] = bolus

    def is_receiving_data(self, timeout_seconds: float = 5.0) -> bool:
        """检查是否正在接收数据"""
        with self._data_lock:
            if self._latest_data["last_update"] is None:
                return False
            elapsed = (
                datetime.now() - self._latest_data["last_update"]
            ).total_seconds()
            return elapsed < timeout_seconds

    def is_connected(self) -> bool:
        """检查是否有客户端连接"""
        return self._client_socket is not None


# 测试代码
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    def on_data_received(data: dict):
        print(
            f"Data received: BG={data['bg']:.1f}, CGM={data['cgm']:.1f}, CHO={data['cho']:.1f}"
        )

    server = TCPServer()

    if not server.start(data_callback=on_data_received):
        print("Failed to start TCP server")
        sys.exit(1)

    print("TCP server started. Press Ctrl+C to stop...")

    try:
        # 模拟设置控制输出
        count = 0
        while True:
            time.sleep(1)

            if server.is_receiving_data():
                # 模拟算法输出
                server.set_control_output(
                    insulin=1.0 + count * 0.1, basal=0.8, bolus=0.2 + count * 0.1
                )
                count += 1

            data = server.get_latest_data()
            print(
                f"Status: Connected={server.is_connected()}, "
                f"Receiving={server.is_receiving_data()}, "
                f"Count={data['received_count']}"
            )

    except KeyboardInterrupt:
        print("\nStopping server...")
        server.stop()
