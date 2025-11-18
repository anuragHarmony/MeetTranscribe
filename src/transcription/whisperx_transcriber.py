"""
WhisperX implementation for speech-to-text with enhanced word-level timestamps
and speaker diarization integration
"""

import numpy as np
from typing import Optional
import logging
from pathlib import Path
import tempfile
import soundfile as sf

from .base import (
    TranscriptionInterface,
    TranscriptionResult,
    Segment,
    Word
)

try:
    import whisperx
except ImportError:
    whisperx = None

logger = logging.getLogger(__name__)


class WhisperXTranscriber(TranscriptionInterface):
    """
    Advanced speech-to-text using WhisperX

    WhisperX provides:
    - 70x faster than realtime with large-v2
    - Word-level timestamps using phoneme alignment
    - Better accuracy than faster-whisper for word boundaries
    - Built-in integration with speaker diarization
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "float16",
        batch_size: int = 16,
        language: Optional[str] = None
    ):
        """
        Initialize WhisperX transcriber

        Args:
            model_size: Model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to use (cpu, cuda)
            compute_type: Computation type (int8, float16, float32)
            batch_size: Batch size for faster processing
            language: Default language code
        """
        if whisperx is None:
            raise ImportError(
                "whisperx is not installed. "
                "Install it with: pip install git+https://github.com/m-bain/whisperX.git"
            )

        self.model_size = model_size
        self.device = self._determine_device(device)
        self.compute_type = compute_type
        self.batch_size = batch_size
        self.default_language = language

        logger.info(
            f"Initializing WhisperX model: {model_size} on {self.device}"
        )

        # Load WhisperX model
        self.model = whisperx.load_model(
            model_size,
            device=self.device,
            compute_type=compute_type
        )

        # Alignment model (loaded on-demand per language)
        self.align_model = None
        self.align_metadata = None
        self.current_align_language = None

    def _determine_device(self, device: str) -> str:
        """Determine best device to use"""
        if device != "auto":
            return device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _load_alignment_model(self, language: str):
        """Load language-specific alignment model"""
        if self.current_align_language == language and self.align_model:
            return

        logger.info(f"Loading alignment model for language: {language}")
        self.align_model, self.align_metadata = whisperx.load_align_model(
            language_code=language,
            device=self.device
        )
        self.current_align_language = language

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio array to text with word-level alignment

        Args:
            audio: Audio data as numpy array (float32)
            sample_rate: Sample rate in Hz
            language: Language code or None for auto-detect

        Returns:
            TranscriptionResult: Transcription with aligned word timestamps
        """
        # Ensure audio is float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # WhisperX expects 16kHz audio
        if sample_rate != 16000:
            logger.warning(f"Resampling from {sample_rate}Hz to 16000Hz")
            import librosa
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=16000
            )
            sample_rate = 16000

        # Transcribe with WhisperX
        result = self.model.transcribe(
            audio,
            batch_size=self.batch_size,
            language=language or self.default_language
        )

        detected_language = result.get("language", language or "en")

        # Align timestamps for word-level accuracy
        self._load_alignment_model(detected_language)

        aligned_result = whisperx.align(
            result["segments"],
            self.align_model,
            self.align_metadata,
            audio,
            self.device,
            return_char_alignments=False
        )

        # Convert to our format
        segments = []
        full_text = []

        for seg in aligned_result["segments"]:
            words = []
            if "words" in seg:
                for word in seg["words"]:
                    words.append(Word(
                        text=word.get("word", ""),
                        start=word.get("start", 0.0),
                        end=word.get("end", 0.0),
                        confidence=word.get("score", 1.0)
                    ))

            segment = Segment(
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=words,
                language=detected_language
            )
            segments.append(segment)
            full_text.append(seg["text"].strip())

        transcription_result = TranscriptionResult(
            text=" ".join(full_text),
            segments=segments,
            language=detected_language,
            duration=segments[-1].end if segments else 0.0,
            metadata={
                "model": self.model_size,
                "device": self.device,
                "aligned": True
            }
        )

        return transcription_result

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
            TranscriptionResult: Transcription with aligned word timestamps
        """
        # Load audio file
        audio = whisperx.load_audio(audio_path)

        return self.transcribe(audio, 16000, language)

    def supports_realtime(self) -> bool:
        """WhisperX supports fast batch processing"""
        return True

    def get_model(self):
        """Get underlying WhisperX model for advanced usage"""
        return self.model

    def get_align_model(self, language: str):
        """Get alignment model for a specific language"""
        self._load_alignment_model(language)
        return self.align_model, self.align_metadata
