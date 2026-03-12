from __future__ import annotations

from dataclasses import dataclass
import json
import socket
import time


@dataclass
class TcpCommandResult:
    applied_u_per_hr: float
    rtt_ms: float | None
    source: str
    raw_reply: dict | None


class RaspberryPiTCPClient:
    """Line-delimited JSON TCP client for Raspberry Pi insulin command RPC."""

    def __init__(
        self,
        host: str,
        port: int,
        timeout_sec: float = 0.5,
        connect_timeout_sec: float = 1.0,
    ):
        self.host = host
        self.port = int(port)
        self.timeout_sec = float(timeout_sec)
        self.connect_timeout_sec = float(connect_timeout_sec)
        self._sock: socket.socket | None = None

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def _ensure_connected(self) -> None:
        if self._sock is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.connect_timeout_sec)
        sock.connect((self.host, self.port))
        sock.settimeout(self.timeout_sec)
        self._sock = sock

    def _recv_line(self) -> str:
        if self._sock is None:
            raise RuntimeError("TCP socket is not connected")
        chunks: list[bytes] = []
        while True:
            b = self._sock.recv(1)
            if not b:
                raise ConnectionError("TCP connection closed by peer")
            if b == b"\n":
                break
            chunks.append(b)
        return b"".join(chunks).decode("utf-8", errors="replace")

    def send_insulin(self, insulin_u_per_hr: float, step: int, glucose: float | None = None) -> TcpCommandResult:
        self._ensure_connected()
        assert self._sock is not None

        payload = {
            "step": int(step),
            "insulin_u_per_hr": float(insulin_u_per_hr),
            "glucose_mg_dl": None if glucose is None else float(glucose),
            "sent_ts_ms": int(time.time() * 1000),
        }

        t0 = time.perf_counter()
        msg = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        self._sock.sendall(msg)
        line = self._recv_line()
        t1 = time.perf_counter()

        rtt_ms = (t1 - t0) * 1000.0
        reply = json.loads(line)

        applied = float(reply.get("applied_u_per_hr", reply.get("insulin_u_per_hr", insulin_u_per_hr)))
        source = str(reply.get("source", "raspi_tcp"))

        return TcpCommandResult(applied_u_per_hr=applied, rtt_ms=rtt_ms, source=source, raw_reply=reply)
