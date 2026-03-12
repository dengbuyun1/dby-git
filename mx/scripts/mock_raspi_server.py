from __future__ import annotations

import argparse
import json
import random
import socket
import time


def handle_client(conn: socket.socket, addr):
    print(f"Client connected: {addr}")
    buffer = b""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                req = json.loads(line.decode("utf-8", errors="replace"))
                cmd = float(req.get("insulin_u_per_hr", 0.0))

                # Emulate actuator saturation and tiny communication jitter.
                applied = max(0.0, min(6.0, cmd))
                time.sleep(random.uniform(0.01, 0.05))

                resp = {
                    "step": req.get("step"),
                    "received_u_per_hr": cmd,
                    "applied_u_per_hr": applied,
                    "source": "mock_raspi",
                    "ack_ts_ms": int(time.time() * 1000),
                }
                conn.sendall((json.dumps(resp, separators=(",", ":")) + "\n").encode("utf-8"))
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        conn.close()
        print(f"Client disconnected: {addr}")


def main():
    parser = argparse.ArgumentParser(description="Mock Raspberry Pi TCP insulin server")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=19090)
    args = parser.parse_args()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((args.host, args.port))
    srv.listen(1)
    print(f"Mock Raspberry server listening on {args.host}:{args.port}")

    try:
        while True:
            conn, addr = srv.accept()
            handle_client(conn, addr)
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()


if __name__ == "__main__":
    main()
