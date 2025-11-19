"""Example: Join and transcribe online meeting."""

import asyncio
import logging
import os

from src.core.config import Config
from src.transcription.service import TranscriptionService

logging.basicConfig(level=logging.INFO)


async def main():
    """Run online meeting example."""
    # Get meeting details from environment or hardcode
    platform = os.getenv("MEETING_PLATFORM", "google_meet")
    meeting_url = os.getenv("MEETING_URL", "https://meet.google.com/xxx-xxxx-xxx")

    # Optional credentials
    credentials = None
    if os.getenv("MEETING_EMAIL") and os.getenv("MEETING_PASSWORD"):
        credentials = {
            "email": os.getenv("MEETING_EMAIL"),
            "password": os.getenv("MEETING_PASSWORD"),
        }

    # Create service
    config = Config()
    service = TranscriptionService(config)

    # Initialize
    await service.initialize()

    print(f"Joining {platform} meeting: {meeting_url}")
    print("Press Ctrl+C to stop\n")

    try:
        # Start online meeting
        async for result in service.start_online_meeting(
            platform, meeting_url, credentials
        ):
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
