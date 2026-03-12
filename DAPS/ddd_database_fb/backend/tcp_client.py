"""TCP client bridge for streaming simulation data to a Raspberry Pi.

The bridge runs in a background thread so the asyncio simulator can enqueue
messages without blocking. If the target address is not configured, the bridge
stays disabled but the rest of the backend keeps working.
"""

from __future__ import annotations

import logging
import os
import queue
import socket
import threading
import time
from typing import Optional

LOGGER = logging.getLogger("TCPBridge")

# 从环境变量读取配置
DEFAULT_HOST = os.getenv("TCP_TARGET_HOST", "")  # 树莓派的IP地址
DEFAULT_PORT = int(os.getenv("TCP_TARGET_PORT", "5000"))  # 默认端口5000
RECONNECT_DELAY = float(os.getenv("TCP_RECONNECT_DELAY", "5"))
MAX_QUEUE_SIZE = int(os.getenv("TCP_QUEUE_SIZE", "512"))
SOCKET_TIMEOUT = float(os.getenv("TCP_SOCKET_TIMEOUT", "10"))


class TCPBridge:
    """管理持久化的TCP连接和发送队列"""

    def __init__(self, host: Optional[str], port: int = DEFAULT_PORT) -> None:
        self.host = host
        self.port = port
        self._queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._thread: Optional[threading.Thread] = None
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._recv_buffer = b""
        self.last_hardware_data = None  # 存储最新的硬件数据

    @property
    def enabled(self) -> bool:
        """检查TCP桥是否已启用"""
        return bool(self.host)

    @property
    def is_connected(self) -> bool:
        """检查是否已连接到TCP服务器"""
        return self._socket is not None

    def start(self) -> None:
        """启动TCP桥接线程"""
        if not self.enabled:
            LOGGER.warning(
                "TCP_TARGET_HOST not set; TCP bridge disabled (will use local simulation only)"
            )
            return

        if self._thread and self._thread.is_alive():
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="tcp-bridge", daemon=True
        )
        self._thread.start()
        LOGGER.info("TCP bridge initialized for %s:%s", self.host, self.port)

    def stop(self) -> None:
        """停止TCP桥接"""
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._close_socket()
        LOGGER.info("TCP bridge stopped")

    def send(self, payload: str) -> None:
        """发送单向消息（不等待响应）"""
        if not self.enabled or not self._running:
            return
        self._enqueue(payload, None)

    def send_stop(self) -> None:
        """发送停止仿真信号"""
        self.send("STOP_SIMULATION")

    def request(self, payload: str, timeout: float = 2.0) -> Optional[str]:
        """发送请求并等待响应"""
        if not self.enabled or not self._running:
            return None
        response_queue: "queue.Queue[str]" = queue.Queue(maxsize=1)
        self._enqueue(payload, response_queue)
        try:
            return response_queue.get(timeout=timeout)
        except queue.Empty:
            LOGGER.warning("TCP response timeout for payload: %s", payload)
            return None

    def _run_loop(self) -> None:
        """主循环：处理连接和消息队列"""
        while self._running:
            if not self._socket and not self._connect():
                time.sleep(RECONNECT_DELAY)
                continue

            try:
                item = self._queue.get(timeout=1)
            except queue.Empty:
                continue

            if item is None:
                break

            payload, response_queue = item

            if not self._send_and_receive(payload, response_queue):
                self._close_socket()
                self._requeue(item)

    def _connect(self) -> bool:
        """尝试连接到TCP服务器"""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(SOCKET_TIMEOUT)
            self._socket.connect((self.host, self.port))
            LOGGER.info("TCP connected to %s:%s", self.host, self.port)
            return True
        except (socket.error, socket.timeout, OSError) as exc:
            LOGGER.warning("TCP connection failed: %s", exc)
            self._close_socket()
            return False

    def _send_and_receive(
        self, payload: str, response_queue: Optional["queue.Queue[str]"]
    ) -> bool:
        """发送数据并接收响应"""
        if not self._socket:
            return False

        try:
            # 发送数据
            self._socket.sendall(payload.encode("utf-8"))
            LOGGER.debug("Sent: %s", payload.strip())

            # 如果需要响应
            if response_queue is not None:
                # 接收响应（以换行符分隔）
                response = self._receive_line()
                if response:
                    LOGGER.debug("Received: %s", response.strip())
                    try:
                        # 尝试解析硬件数据
                        import json

                        data = json.loads(response)
                        if "hardware" in data:
                            self.last_hardware_data = data["hardware"]

                        response_queue.put_nowait(response)
                    except (json.JSONDecodeError, queue.Full):
                        if isinstance(response, str):  # 如果不是JSON，直接放入队列
                            try:
                                response_queue.put_nowait(response)
                            except queue.Full:
                                pass
                        LOGGER.warning("Response processing error or queue full")
                    return True
                else:
                    LOGGER.warning("No response received")
                    return False
            return True

        except (socket.error, socket.timeout, OSError) as exc:
            LOGGER.error("TCP send/receive error: %s", exc)
            return False

    def _receive_line(self, max_length: int = 4096) -> Optional[str]:
        """接收一行数据（以换行符结尾）"""
        if not self._socket:
            return None

        try:
            while b"\n" not in self._recv_buffer:
                chunk = self._socket.recv(1024)
                if not chunk:
                    LOGGER.warning("Connection closed by server")
                    return None
                self._recv_buffer += chunk
                if len(self._recv_buffer) > max_length:
                    LOGGER.error("Buffer overflow, clearing")
                    self._recv_buffer = b""
                    return None

            # 分割出一行
            line, self._recv_buffer = self._recv_buffer.split(b"\n", 1)
            return line.decode("utf-8").strip()

        except (socket.error, socket.timeout, UnicodeDecodeError) as exc:
            LOGGER.error("Receive error: %s", exc)
            return None

    def _close_socket(self) -> None:
        """关闭socket连接"""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            finally:
                self._socket = None
                self._recv_buffer = b""

    def _enqueue(
        self, payload: str, response_queue: Optional["queue.Queue[str]"]
    ) -> None:
        """将消息加入发送队列"""
        if not payload.endswith("\n"):
            payload = f"{payload}\n"
        try:
            self._queue.put_nowait((payload, response_queue))
        except queue.Full:
            LOGGER.warning("TCP send queue full; dropping payload")

    def _requeue(self, item: tuple[str, Optional["queue.Queue[str]"]]) -> None:
        """重新加入队列（连接失败时）"""
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            LOGGER.warning("TCP queue full while requeuing message")


def create_bridge(
    host: Optional[str] = None, port: int = DEFAULT_PORT
) -> Optional[TCPBridge]:
    """创建并启动TCP桥接

    Args:
        host: 树莓派IP地址，如果为None则使用环境变量TCP_TARGET_HOST
        port: TCP端口，默认使用环境变量TCP_TARGET_PORT或5000
    """
    target_host = host if host is not None else DEFAULT_HOST
    bridge = TCPBridge(host=target_host, port=port)
    if bridge.enabled:
        bridge.start()
        return bridge
    LOGGER.info(
        "TCP bridge not started (TCP_TARGET_HOST unset - using local simulation only)"
    )
    return None
