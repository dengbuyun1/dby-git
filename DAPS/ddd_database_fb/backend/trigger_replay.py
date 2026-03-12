import asyncio
import websockets
import json
import sys


async def trigger_replay(patient_id):
    uri = "ws://localhost:8766"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")

            # Send start_replay command
            command = {"command": "start_replay", "patient_id": patient_id}
            await websocket.send(json.dumps(command))
            print(f"Sent command: {command}")

            print(
                "Replay started. Press Ctrl+C to stop monitoring (replay continues on server)."
            )

            # Keep connection open to receive data
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                if data.get("type") == "base_data":
                    print(
                        f"Received data: {data.get('timestamp')} BG:{data.get('bg')} Insulin:{data.get('insulin')}"
                    )
                elif data.get("type") == "status_update":
                    pass  # Ignore status updates
                else:
                    print(f"Received message: {data}")

    except ConnectionRefusedError:
        print("Could not connect to simulator. Is it running?")
    except websockets.exceptions.ConnectionClosed:
        print("Connection closed")


if __name__ == "__main__":
    patient_id = "P01"
    if len(sys.argv) > 1:
        patient_id = sys.argv[1]

    try:
        asyncio.run(trigger_replay(patient_id))
    except KeyboardInterrupt:
        print("Stopped")
