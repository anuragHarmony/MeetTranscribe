"""Tests for transcription module."""

import numpy as np
import pytest

from src.core.config import WhisperConfig
from src.core.interfaces import AudioChunk, AudioSource
from src.transcription.whisper_engine import WhisperTranscriptionEngine


@pytest.fixture
def whisper_config():
    """Create Whisper config for testing."""
    return WhisperConfig(
        model_size="tiny",  # Use tiny for faster tests
        device="cpu",
    )


@pytest.fixture
async def whisper_engine(whisper_config):
    """Create and initialize Whisper engine."""
    engine = WhisperTranscriptionEngine(whisper_config)
    await engine.initialize()
    return engine


def create_dummy_audio_chunk(duration_s=3, sample_rate=16000):
    """Create dummy audio chunk for testing."""
    audio_data = np.random.randn(sample_rate * duration_s).astype(np.float32)
    return AudioChunk(
        data=audio_data,
        sample_rate=sample_rate,
        timestamp=None,
        source=AudioSource.LOCAL_MIC,
        duration_ms=duration_s * 1000,
    )


@pytest.mark.asyncio
async def test_whisper_initialization(whisper_config):
    """Test Whisper engine initialization."""
    engine = WhisperTranscriptionEngine(whisper_config)
    assert not engine._is_initialized

    await engine.initialize()
    assert engine._is_initialized
    assert engine.model is not None


@pytest.mark.asyncio
async def test_whisper_transcribe(whisper_engine):
    """Test basic transcription."""
    audio = create_dummy_audio_chunk()
    segments = await whisper_engine.transcribe(audio)

    assert isinstance(segments, list)
    # Segments may be empty for random noise
