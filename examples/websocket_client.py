"""Example: WebSocket client for real-time transcription."""

import asyncio
import json

import websockets


async def local_recording_client():
    """Connect to local recording WebSocket."""
    uri = "ws://localhost:8000/ws/local"

    async with websockets.connect(uri) as websocket:
        # Send start request
        await websocket.send(json.dumps({"capture_mode": "combined"}))

        print("Connected to local recording WebSocket")
        print("Receiving transcriptions...\n")

        # Receive transcriptions
        try:
            while True:
                message = await websocket.recv()
                result = json.loads(message)

                if "error" in result:
                    print(f"Error: {result['error']}")
                    break

                print(f"\n[{result['timestamp']}]")
                for segment in result["segments"]:
                    speaker = segment.get("speaker_name") or segment.get(
                        "speaker_id", "Unknown"
                    )
                    text = segment["text"]
                    print(f"  [{speaker}] {text}")

        except KeyboardInterrupt:
            print("\nStopping...")


async def online_meeting_client():
    """Connect to online meeting WebSocket."""
    uri = "ws://localhost:8000/ws/online"

    async with websockets.connect(uri) as websocket:
        # Send start request
        await websocket.send(
            json.dumps(
                {
                    "platform": "google_meet",
                    "meeting_url": "https://meet.google.com/xxx-xxxx-xxx",
                    "credentials": None,  # Optional
                }
            )
        )

        print("Connected to online meeting WebSocket")
        print("Receiving transcriptions...\n")

        # Receive transcriptions
        try:
            while True:
                message = await websocket.recv()
                result = json.loads(message)

                if "error" in result:
                    print(f"Error: {result['error']}")
                    break

                print(f"\n[{result['timestamp']}]")
                for segment in result["segments"]:
                    speaker = segment.get("speaker_name") or segment.get(
                        "speaker_id", "Unknown"
                    )
                    text = segment["text"]
                    print(f"  [{speaker}] {text}")

        except KeyboardInterrupt:
            print("\nStopping...")


if __name__ == "__main__":
    # Choose which example to run
    mode = input("Choose mode (local/online): ").strip().lower()

    if mode == "local":
        asyncio.run(local_recording_client())
    elif mode == "online":
        asyncio.run(online_meeting_client())
    else:
        print("Invalid mode. Choose 'local' or 'online'")
