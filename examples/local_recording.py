"""Example: Local audio recording and transcription."""

import asyncio
import logging

from src.core.config import Config
from src.transcription.service import TranscriptionService

logging.basicConfig(level=logging.INFO)


async def main():
    """Run local recording example."""
    # Create service
    config = Config()
    service = TranscriptionService(config)

    # Initialize
    await service.initialize()

    print("Starting local recording...")
    print("Press Ctrl+C to stop\n")

    try:
        # Start recording with combined audio (mic + system)
        async for result in service.start_local_recording(capture_mode="combined"):
            print(f"\n[{result['timestamp']}]")

            for segment in result["segments"]:
                speaker = segment.get("speaker_name") or segment.get(
                    "speaker_id", "Unknown"
                )
                text = segment["text"]
                confidence = segment["confidence"]

                print(f"  [{speaker}] {text} (confidence: {confidence:.2f})")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
