"""
Speaker diarization module for identifying "who spoke when"
"""

from .base import DiarizationInterface, DiarizationResult, SpeakerSegment
from .pyannote_diarizer import PyAnnoteDiarizer

__all__ = [
    "DiarizationInterface",
    "DiarizationResult",
    "SpeakerSegment",
    "PyAnnoteDiarizer"
]
