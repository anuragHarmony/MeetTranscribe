"""
Speech-to-text transcription module
"""

from .base import TranscriptionInterface, TranscriptionResult
from .whisper_transcriber import WhisperTranscriber
from .whisperx_transcriber import WhisperXTranscriber

__all__ = [
    "TranscriptionInterface",
    "TranscriptionResult",
    "WhisperTranscriber",
    "WhisperXTranscriber"
]
