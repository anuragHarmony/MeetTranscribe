"""
Base interfaces for transcription following SOLID principles
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class Word:
    """Represents a single word with timing information"""
    text: str
    start: float
    end: float
    confidence: float = 1.0


@dataclass
class Segment:
    """Represents a speech segment"""
    text: str
    start: float
    end: float
    words: List[Word] = field(default_factory=list)
    speaker: Optional[str] = None
    language: Optional[str] = None
    confidence: float = 1.0


@dataclass
class TranscriptionResult:
    """
    Complete transcription result with metadata
    """
    text: str
    segments: List[Segment]
    language: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class TranscriptionInterface(ABC):
    """
    Interface for speech-to-text transcription (Interface Segregation Principle)
    """

    @abstractmethod
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: Optional[str] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio to text

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            language: Language code (e.g., 'en', 'es') or None for auto-detect

        Returns:
            TranscriptionResult: Transcription with segments and metadata
        """
        pass

    @abstractmethod
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
            TranscriptionResult: Transcription with segments and metadata
        """
        pass

    @abstractmethod
    def supports_realtime(self) -> bool:
        """Check if real-time transcription is supported"""
        pass


class RealtimeTranscriptionInterface(ABC):
    """
    Interface for real-time/streaming transcription
    """

    @abstractmethod
    def transcribe_stream(
        self,
        audio_stream,
        sample_rate: int,
        language: Optional[str] = None
    ):
        """
        Transcribe audio stream in real-time

        Args:
            audio_stream: Generator yielding audio chunks
            sample_rate: Sample rate in Hz
            language: Language code or None for auto-detect

        Yields:
            TranscriptionResult: Partial transcription results
        """
        pass
