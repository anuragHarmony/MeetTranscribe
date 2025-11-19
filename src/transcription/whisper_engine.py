"""Whisper-based transcription engine."""

import asyncio
import logging
from typing import AsyncIterator, List, Optional

import numpy as np
import torch
import whisper
from whisper import Whisper

from src.core.config import WhisperConfig
from src.core.interfaces import AudioChunk, ITranscriptionEngine, TranscriptionSegment

logger = logging.getLogger(__name__)


class WhisperTranscriptionEngine(ITranscriptionEngine):
    """OpenAI Whisper-based transcription engine."""

    def __init__(self, config: WhisperConfig):
        """
        Initialize Whisper engine.

        Args:
            config: Whisper configuration
        """
        self.config = config
        self.model: Optional[Whisper] = None
        self._is_initialized = False
        self._buffer: List[np.ndarray] = []
        self._buffer_duration_s = 30  # Process every 30 seconds of audio

    async def initialize(self) -> None:
        """Initialize Whisper model."""
        if self._is_initialized:
            logger.warning("Whisper already initialized")
            return

        logger.info(f"Loading Whisper model: {self.config.model_size}")

        # Load model in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None,
            whisper.load_model,
            self.config.model_size,
            self.config.device,
        )

        self._is_initialized = True
        logger.info(f"Whisper model loaded on {self.config.device}")

    async def transcribe(self, audio: AudioChunk) -> List[TranscriptionSegment]:
        """
        Transcribe audio chunk.

        Args:
            audio: Audio chunk to transcribe

        Returns:
            List of transcription segments
        """
        if not self._is_initialized or self.model is None:
            raise RuntimeError("Whisper engine not initialized")

        # Convert audio to float32 and normalize
        audio_data = audio.data.astype(np.float32)
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0  # Normalize int16 to float32

        # Ensure audio is at least 1 second
        min_samples = audio.sample_rate
        if len(audio_data) < min_samples:
            audio_data = np.pad(audio_data, (0, min_samples - len(audio_data)))

        # Run transcription in thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._transcribe_sync,
            audio_data,
            audio.sample_rate,
        )

        # Convert result to TranscriptionSegments
        segments = []
        for segment in result.get("segments", []):
            segments.append(
                TranscriptionSegment(
                    text=segment["text"].strip(),
                    start_time=segment["start"],
                    end_time=segment["end"],
                    confidence=segment.get("confidence", 0.0),
                    language=result.get("language"),
                )
            )

        return segments

    def _transcribe_sync(self, audio_data: np.ndarray, sample_rate: int) -> dict:
        """
        Synchronous transcription (runs in thread pool).

        Args:
            audio_data: Audio data as float32 numpy array
            sample_rate: Sample rate

        Returns:
            Whisper transcription result
        """
        # Resample if needed (Whisper expects 16kHz)
        if sample_rate != 16000:
            # Simple resampling (for production, use librosa.resample)
            ratio = 16000 / sample_rate
            new_length = int(len(audio_data) * ratio)
            audio_data = np.interp(
                np.linspace(0, len(audio_data), new_length),
                np.arange(len(audio_data)),
                audio_data,
            )

        # Transcribe with Whisper
        result = self.model.transcribe(
            audio_data,
            language=self.config.language,
            task=self.config.task,
            beam_size=self.config.beam_size,
            best_of=self.config.best_of,
            temperature=self.config.temperature,
            fp16=(self.config.device == "cuda" and self.config.compute_type == "float16"),
        )

        # Add confidence scores (Whisper doesn't provide them directly)
        # We'll use a heuristic based on the no_speech_prob
        for segment in result.get("segments", []):
            segment["confidence"] = 1.0 - result.get("no_speech_prob", 0.0)

        return result

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[TranscriptionSegment]:
        """
        Transcribe audio stream in real-time.

        Args:
            audio_stream: Stream of audio chunks

        Yields:
            Transcription segments
        """
        if not self._is_initialized or self.model is None:
            raise RuntimeError("Whisper engine not initialized")

        buffer = []
        buffer_duration_ms = 0
        target_duration_ms = self._buffer_duration_s * 1000

        async for chunk in audio_stream:
            buffer.append(chunk)
            buffer_duration_ms += chunk.duration_ms

            # Process when buffer reaches target duration
            if buffer_duration_ms >= target_duration_ms:
                # Concatenate audio chunks
                audio_data = np.concatenate([c.data for c in buffer])
                sample_rate = buffer[0].sample_rate

                # Create combined chunk
                combined_chunk = AudioChunk(
                    data=audio_data,
                    sample_rate=sample_rate,
                    timestamp=buffer[0].timestamp,
                    source=buffer[0].source,
                    duration_ms=buffer_duration_ms,
                )

                # Transcribe
                segments = await self.transcribe(combined_chunk)

                # Yield segments
                for segment in segments:
                    yield segment

                # Clear buffer
                buffer.clear()
                buffer_duration_ms = 0

        # Process remaining buffer
        if buffer:
            audio_data = np.concatenate([c.data for c in buffer])
            sample_rate = buffer[0].sample_rate

            combined_chunk = AudioChunk(
                data=audio_data,
                sample_rate=sample_rate,
                timestamp=buffer[0].timestamp,
                source=buffer[0].source,
                duration_ms=buffer_duration_ms,
            )

            segments = await self.transcribe(combined_chunk)
            for segment in segments:
                yield segment
