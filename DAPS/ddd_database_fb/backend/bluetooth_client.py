"""Bluetooth client bridge for streaming simulation data to a Raspberry Pi.

The bridge runs in a background thread so the asyncio simulator can enqueue
messages without blocking. If PyBluez is unavailable or no target address is
configured, the bridge stays disabled but the rest of the backend keeps working.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Optional

try:
    import bluetooth  # type: ignore
except ImportError:  # pragma: no cover - Bluetooth support is optional during dev
    bluetooth = None  # type: ignore


LOGGER = logging.getLogger("BluetoothBridge")

DEFAULT_ADDRESS = os.getenv("BLUETOOTH_TARGET_ADDRESS")
DEFAULT_PORT = int(os.getenv("BLUETOOTH_TARGET_PORT", "2"))
RECONNECT_DELAY = float(os.getenv("BLUETOOTH_RECONNECT_DELAY", "5"))
MAX_QUEUE_SIZE = int(os.getenv("BLUETOOTH_QUEUE_SIZE", "512"))


class BluetoothBridge:
    """Manages a persistent RFCOMM connection and a send queue."""

    def __init__(self, address: Optional[str], port: int = DEFAULT_PORT) -> None:
        self.address = address
        self.port = port
        self._queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._thread: Optional[threading.Thread] = None
        self._socket = None
        self._running = False
        self._recv_buffer = b""

    @property
    def enabled(self) -> bool:
        return bluetooth is not None and bool(self.address)

    def start(self) -> None:
        if not self.enabled:
            if bluetooth is None:
                LOGGER.warning("PyBluez not installed; Bluetooth bridge disabled")
            else:
                LOGGER.warning(
                    "BLUETOOTH_TARGET_ADDRESS not set; Bluetooth bridge disabled"
                )
            return

        if self._thread and self._thread.is_alive():
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, name="bt-bridge", daemon=True
        )
        self._thread.start()
        LOGGER.info("Bluetooth bridge initialised for %s:%s", self.address, self.port)

    def stop(self) -> None:
        self._running = False
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        self._close_socket()
        LOGGER.info("Bluetooth bridge stopped")

    def send(self, payload: str) -> None:
        if not self.enabled or not self._running:
            return
        self._enqueue(payload, None)

    def send_stop(self) -> None:
        self.send("STOP_SIMULATION")

    def request(self, payload: str, timeout: float = 2.0) -> Optional[str]:
        if not self.enabled or not self._running:
            return None
        response_queue: "queue.Queue[str]" = queue.Queue(maxsize=1)
        self._enqueue(payload, response_queue)
        try:
            return response_queue.get(timeout=timeout)
        except queue.Empty:
            LOGGER.warning("Bluetooth response timeout for payload: %s", payload)
            return None

    def _run_loop(self) -> None:
        while self._running:
            if not self._socket and not self._connect():
                time.sleep(RECONNECT_DELAY)
                continue

            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if item is None:  # shutdown signal
                continue

            if not self._socket:
                # Connection dropped; requeue and retry next loop
                self._requeue(item)
                continue

            payload, response_queue = item

            try:
                self._socket.send(payload.encode("utf-8"))
                response = self._receive_message()
                if response_queue is not None and response is not None:
                    try:
                        response_queue.put_nowait(response)
                    except queue.Full:
                        LOGGER.debug("Response queue full; dropping response")
            except Exception as exc:  # noqa: BLE001 - bluetooth errors vary by platform
                LOGGER.error("Bluetooth send failed: %s", exc)
                self._requeue((payload, response_queue))
                self._close_socket()
                time.sleep(RECONNECT_DELAY)

    def _connect(self) -> bool:
        if not self.enabled:
            return False

        try:
            sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)  # type: ignore[attr-defined]
            sock.connect((self.address, self.port))
            sock.settimeout(2.0)
            self._socket = sock
            LOGGER.info("Bluetooth connected to %s:%s", self.address, self.port)
            return True
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Bluetooth connection failed: %s", exc)
            self._close_socket()
            return False

    def _receive_message(self, timeout: float = 2.0) -> Optional[str]:
        if not self._socket:
            return None

        end_time = time.time() + timeout
        while time.time() < end_time:
            if b"\n" in self._recv_buffer:
                message, _, remainder = self._recv_buffer.partition(b"\n")
                self._recv_buffer = remainder
                return message.decode("utf-8", errors="ignore").strip()

            try:
                chunk = self._socket.recv(1024)
            except Exception as exc:  # noqa: BLE001
                LOGGER.error("Bluetooth receive failed: %s", exc)
                return None

            if not chunk:
                return None

            self._recv_buffer += chunk

        if self._recv_buffer:
            message = self._recv_buffer.decode("utf-8", errors="ignore").strip()
            self._recv_buffer = b""
            return message
        return None

    def _close_socket(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        except Exception:  # noqa: BLE001
            pass
        finally:
            self._socket = None

    def _enqueue(
        self, payload: str, response_queue: Optional["queue.Queue[str]"]
    ) -> None:
        if not payload.endswith("\n"):
            payload = f"{payload}\n"
        try:
            self._queue.put_nowait((payload, response_queue))
        except queue.Full:
            LOGGER.warning("Bluetooth send queue full; dropping payload")

    def _requeue(self, item: tuple[str, Optional["queue.Queue[str]"]]) -> None:
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            LOGGER.warning("Bluetooth queue full while requeuing message")


def create_bridge() -> Optional[BluetoothBridge]:
    bridge = BluetoothBridge(address=DEFAULT_ADDRESS, port=DEFAULT_PORT)
    if bridge.enabled:
        bridge.start()
        return bridge
    LOGGER.info(
        "Bluetooth bridge not started (PyBluez missing or BLUETOOTH_TARGET_ADDRESS unset)"
    )
    return None
