"""
Faster-Whisper implementation for speech-to-text transcription
"""

import numpy as np
from typing import Optional, List
import logging
from pathlib import Path

from .base import (
    TranscriptionInterface,
    TranscriptionResult,
    Segment,
    Word
)

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None

logger = logging.getLogger(__name__)


class WhisperTranscriber(TranscriptionInterface):
    """
    High-performance speech-to-text using faster-whisper

    faster-whisper is 4x faster than OpenAI's Whisper with CTranslate2
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        download_root: Optional[str] = None,
        num_workers: int = 1
    ):
        """
        Initialize Whisper transcriber

        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3, large-v3-turbo, distil-large-v3)
            device: Device to use (cpu, cuda, auto)
            compute_type: Computation type (int8, int16, float16, float32, auto)
            download_root: Directory to store models
            num_workers: Number of workers for parallel processing

        Note:
            - large-v3-turbo: 6x faster than large-v3, ~12% WER (recommended)
            - distil-large-v3: 5x faster than large-v3, ~11% WER
            - large-v3: Best accuracy, ~10% WER, slowest
        """
        if WhisperModel is None:
            raise ImportError(
                "faster-whisper is not installed. "
                "Install it with: pip install faster-whisper"
            )

        self.model_size = model_size
        self.device = self._determine_device(device)
        self.compute_type = self._determine_compute_type(compute_type)

        logger.info(
            f"Initializing Whisper model: {model_size} on {self.device} "
            f"with {self.compute_type} precision"
        )

        self.model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=self.compute_type,
            download_root=download_root,
            num_workers=num_workers
        )

    def _determine_device(self, device: str) -> str:
        """Determine best device to use"""
        if device != "auto":
            return device

        import torch
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _determine_compute_type(self, compute_type: str) -> str:
        """Determine best compute type based on device"""
        if compute_type != "auto":
            return compute_type

        if self.device == "cuda":
            return "float16"  # Best for GPU
        return "int8"  # Best for CPU

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio array to text

        Args:
            audio: Audio data as numpy array (float32, normalized to [-1, 1])
            sample_rate: Sample rate in Hz
            language: Language code (e.g., 'en') or None for auto-detect

        Returns:
            TranscriptionResult: Transcription with segments
        """
        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Transcribe with faster-whisper
        segments_iter, info = self.model.transcribe(
            audio,
            language=language,
            word_timestamps=True,
            vad_filter=True,  # Use VAD to filter silence
            beam_size=5
        )

        # Convert segments to our format
        segments = []
        full_text = []

        for segment in segments_iter:
            # Convert words
            words = []
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    words.append(Word(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                        confidence=word.probability
                    ))

            seg = Segment(
                text=segment.text.strip(),
                start=segment.start,
                end=segment.end,
                words=words,
                language=info.language,
                confidence=segment.avg_logprob
            )
            segments.append(seg)
            full_text.append(segment.text.strip())

        result = TranscriptionResult(
            text=" ".join(full_text),
            segments=segments,
            language=info.language,
            duration=segments[-1].end if segments else 0.0,
            metadata={
                "model": self.model_size,
                "language_probability": info.language_probability,
                "device": self.device,
                "compute_type": self.compute_type
            }
        )

        return result

    def transcribe_file(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file to text

        Args:
            audio_path: Path to audio file
            language: Language code or None for auto-detect

        Returns:
            TranscriptionResult: Transcription with segments
        """
        segments_iter, info = self.model.transcribe(
            audio_path,
            language=language,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5
        )

        segments = []
        full_text = []

        for segment in segments_iter:
            words = []
            if hasattr(segment, 'words') and segment.words:
                for word in segment.words:
                    words.append(Word(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                        confidence=word.probability
                    ))

            seg = Segment(
                text=segment.text.strip(),
                start=segment.start,
                end=segment.end,
                words=words,
                language=info.language,
                confidence=segment.avg_logprob
            )
            segments.append(seg)
            full_text.append(segment.text.strip())

        result = TranscriptionResult(
            text=" ".join(full_text),
            segments=segments,
            language=info.language,
            duration=segments[-1].end if segments else 0.0,
            metadata={
                "model": self.model_size,
                "language_probability": info.language_probability,
                "file": audio_path
            }
        )

        return result

    def supports_realtime(self) -> bool:
        """faster-whisper supports pseudo-realtime with chunking"""
        return True
