"""
PyAnnote.audio implementation for speaker diarization

Uses the latest pyannote.audio 4.0 with community-1 model (SOTA 2025)
"""

import numpy as np
from typing import Optional
import logging
import tempfile
import soundfile as sf
from pathlib import Path

from .base import (
    DiarizationInterface,
    DiarizationResult,
    SpeakerSegment
)

try:
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation
except ImportError:
    Pipeline = None
    Annotation = None

logger = logging.getLogger(__name__)


class PyAnnoteDiarizer(DiarizationInterface):
    """
    State-of-the-art speaker diarization using pyannote.audio

    PyAnnote.audio 4.0 with community-1 model provides:
    - Best open-source diarization performance (2025)
    - Accurate speaker segmentation
    - Handles overlapping speech
    - Robust to various acoustic conditions
    """

    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        use_auth_token: Optional[str] = None,
        device: str = "auto"
    ):
        """
        Initialize PyAnnote diarizer

        Args:
            model_name: Model identifier from HuggingFace
                       - "pyannote/speaker-diarization-3.1" (legacy, free)
                       - "pyannote/speaker-diarization-community-1" (latest, requires token)
            use_auth_token: HuggingFace auth token (required for community-1 and precision-2)
            device: Device to use (cpu, cuda, auto)
        """
        if Pipeline is None:
            raise ImportError(
                "pyannote.audio is not installed. "
                "Install it with: pip install pyannote.audio"
            )

        self.model_name = model_name
        self.device = self._determine_device(device)

        logger.info(f"Initializing PyAnnote diarization: {model_name} on {self.device}")

        # Load pipeline
        try:
            if use_auth_token:
                self.pipeline = Pipeline.from_pretrained(
                    model_name,
                    use_auth_token=use_auth_token
                )
            else:
                self.pipeline = Pipeline.from_pretrained(model_name)

            # Move to device
            if self.device == "cuda":
                import torch
                self.pipeline.to(torch.device("cuda"))

        except Exception as e:
            logger.error(f"Failed to load PyAnnote pipeline: {e}")
            logger.info(
                "If using community-1 or precision-2, you need a HuggingFace token. "
                "Get one at https://huggingface.co/settings/tokens and accept model terms."
            )
            raise

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

    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> DiarizationResult:
        """
        Perform speaker diarization on audio array

        Args:
            audio: Audio data as numpy array (mono, float32)
            sample_rate: Sample rate in Hz
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            DiarizationResult: Diarization with speaker segments
        """
        # Ensure audio is float32 and mono
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # PyAnnote expects 16kHz audio
        if sample_rate != 16000:
            logger.warning(f"Resampling from {sample_rate}Hz to 16000Hz")
            import librosa
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=16000
            )
            sample_rate = 16000

        # Save to temporary file (PyAnnote works better with files)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            sf.write(tmp_path, audio, sample_rate)

        try:
            result = self.diarize_file(
                tmp_path,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers
            )
            return result
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def diarize_file(
        self,
        audio_path: str,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> DiarizationResult:
        """
        Perform speaker diarization on audio file

        Args:
            audio_path: Path to audio file
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            DiarizationResult: Diarization with speaker segments
        """
        # Build parameters
        params = {}
        if num_speakers is not None:
            params["num_speakers"] = num_speakers
        else:
            if min_speakers is not None:
                params["min_speakers"] = min_speakers
            if max_speakers is not None:
                params["max_speakers"] = max_speakers

        # Perform diarization
        logger.info(f"Diarizing audio file: {audio_path}")
        diarization: Annotation = self.pipeline(audio_path, **params)

        # Convert to our format
        segments = []
        speakers_set = set()

        for turn, _, speaker in diarization.itertracks(yield_label=True):
            segment = SpeakerSegment(
                speaker_id=speaker,
                start=turn.start,
                end=turn.end,
                confidence=1.0  # PyAnnote doesn't provide per-segment confidence
            )
            segments.append(segment)
            speakers_set.add(speaker)

        # Sort segments by start time
        segments.sort(key=lambda x: x.start)

        # Get audio duration
        import soundfile as sf
        audio_info = sf.info(audio_path)
        duration = audio_info.duration

        result = DiarizationResult(
            segments=segments,
            num_speakers=len(speakers_set),
            duration=duration,
            metadata={
                "model": self.model_name,
                "device": self.device,
                "speakers": list(speakers_set)
            }
        )

        logger.info(
            f"Diarization complete: {result.num_speakers} speakers, "
            f"{len(segments)} segments"
        )

        return result

    def get_pipeline(self) -> Pipeline:
        """Get underlying PyAnnote pipeline for advanced usage"""
        return self.pipeline
