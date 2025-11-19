"""Example: Create voice profile from audio samples."""

import asyncio
import logging

import numpy as np

from src.core.config import Config
from src.core.interfaces import AudioChunk, AudioSource
from src.transcription.service import TranscriptionService

logging.basicConfig(level=logging.INFO)


async def main():
    """Create voice profile example."""
    # Create service
    config = Config()
    service = TranscriptionService(config)

    # Initialize
    await service.initialize()

    # In a real scenario, you would:
    # 1. Record audio samples from the person
    # 2. Extract segments with only that person speaking
    # 3. Create profile from those samples

    # For this example, we'll create dummy samples
    # In production, use actual audio recordings
    print("Creating voice profile...")
    print("Note: This is a dummy example. Use real audio samples in production.\n")

    # Create dummy audio samples (in production, load from files or recordings)
    sample_rate = 16000
    duration_s = 3
    num_samples = 5

    audio_samples = []
    for i in range(num_samples):
        # Create dummy audio data
        audio_data = np.random.randn(sample_rate * duration_s).astype(np.float32)

        chunk = AudioChunk(
            data=audio_data,
            sample_rate=sample_rate,
            timestamp=asyncio.get_event_loop().time(),
            source=AudioSource.LOCAL_MIC,
            duration_ms=duration_s * 1000,
        )
        audio_samples.append(chunk)

    # Create profile
    profile = await service.create_voice_profile(
        name="John Doe",
        email="john.doe@example.com",
        audio_samples=audio_samples,
    )

    print(f"Voice profile created!")
    print(f"  ID: {profile.profile_id}")
    print(f"  Name: {profile.name}")
    print(f"  Email: {profile.email}")
    print(f"  Samples: {profile.sample_count}")


if __name__ == "__main__":
    asyncio.run(main())
