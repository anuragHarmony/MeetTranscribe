"""Speaker diarization using pyannote.audio."""

import asyncio
import io
import logging
from typing import List, Optional

import numpy as np
import torch
from pyannote.audio import Pipeline
from pydub import AudioSegment

from src.core.config import DiarizationConfig
from src.core.interfaces import AudioChunk, ISpeakerDiarization, SpeakerSegment

logger = logging.getLogger(__name__)


class PyAnnoteDiarization(ISpeakerDiarization):
    """Speaker diarization using pyannote.audio."""

    def __init__(self, config: DiarizationConfig):
        """
        Initialize diarization engine.

        Args:
            config: Diarization configuration
        """
        self.config = config
        self.pipeline: Optional[Pipeline] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize diarization pipeline."""
        if self._is_initialized:
            logger.warning("Diarization already initialized")
            return

        logger.info(f"Loading diarization model: {self.config.model_name}")

        # Load pipeline in thread pool
        loop = asyncio.get_event_loop()
        self.pipeline = await loop.run_in_executor(
            None,
            self._load_pipeline,
        )

        self._is_initialized = True
        logger.info(f"Diarization model loaded on {self.config.device}")

    def _load_pipeline(self) -> Pipeline:
        """Load pyannote pipeline (runs in thread pool)."""
        # Note: This requires HuggingFace authentication token
        # Users need to set HUGGINGFACE_TOKEN environment variable
        try:
            pipeline = Pipeline.from_pretrained(
                self.config.model_name,
                use_auth_token=True,
            )

            # Move to device
            if self.config.device == "cuda" and torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))

            return pipeline
        except Exception as e:
            logger.warning(f"Failed to load pyannote pipeline with auth: {e}")
            logger.info("Attempting to load without authentication...")
            # Fallback: try without authentication
            pipeline = Pipeline.from_pretrained(self.config.model_name)
            if self.config.device == "cuda" and torch.cuda.is_available():
                pipeline.to(torch.device("cuda"))
            return pipeline

    async def diarize(self, audio: AudioChunk) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on audio.

        Args:
            audio: Audio chunk to diarize

        Returns:
            List of speaker segments
        """
        if not self._is_initialized or self.pipeline is None:
            raise RuntimeError("Diarization engine not initialized")

        # Convert numpy array to audio file in memory
        audio_data = audio.data.astype(np.float32)
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0  # Normalize int16 to float32

        # Scale to int16 for pydub
        audio_data_int16 = (audio_data * 32767).astype(np.int16)

        # Create audio segment
        audio_segment = AudioSegment(
            audio_data_int16.tobytes(),
            frame_rate=audio.sample_rate,
            sample_width=2,  # 16-bit
            channels=1,
        )

        # Export to wav in memory
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)

        # Run diarization in thread pool
        loop = asyncio.get_event_loop()
        diarization = await loop.run_in_executor(
            None,
            self._diarize_sync,
            wav_io,
        )

        # Convert to SpeakerSegments
        segments = []
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segments.append(
                SpeakerSegment(
                    speaker_id=speaker,
                    start_time=turn.start,
                    end_time=turn.end,
                    confidence=1.0,  # pyannote doesn't provide confidence
                )
            )

        logger.debug(f"Diarized {len(segments)} speaker segments")
        return segments

    def _diarize_sync(self, audio_file):
        """
        Synchronous diarization (runs in thread pool).

        Args:
            audio_file: Audio file-like object

        Returns:
            Diarization result
        """
        params = {}
        if self.config.min_speakers is not None:
            params["min_speakers"] = self.config.min_speakers
        if self.config.max_speakers is not None:
            params["max_speakers"] = self.config.max_speakers

        diarization = self.pipeline(audio_file, **params)
        return diarization
