"""Tests for audio capture module."""

import asyncio

import numpy as np
import pytest

from src.audio.capture import LocalAudioCapture
from src.core.config import AudioConfig


@pytest.fixture
def audio_config():
    """Create audio config for testing."""
    return AudioConfig(
        sample_rate=16000,
        channels=1,
        chunk_duration_ms=100,
    )


@pytest.mark.asyncio
async def test_local_audio_capture_start_stop(audio_config):
    """Test starting and stopping local audio capture."""
    capture = LocalAudioCapture(audio_config)

    # Initially not active
    assert not capture.is_active()

    # Start capture
    await capture.start()
    assert capture.is_active()

    # Stop capture
    await capture.stop()
    assert not capture.is_active()


@pytest.mark.asyncio
async def test_local_audio_capture_stream(audio_config):
    """Test audio stream from local capture."""
    capture = LocalAudioCapture(audio_config)
    await capture.start()

    chunks_received = 0
    async for chunk in capture.get_audio_stream():
        assert chunk.sample_rate == audio_config.sample_rate
        assert isinstance(chunk.data, np.ndarray)
        chunks_received += 1

        if chunks_received >= 3:
            break

    await capture.stop()
    assert chunks_received == 3
