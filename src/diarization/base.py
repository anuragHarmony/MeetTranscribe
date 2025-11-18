"""
Base interfaces for speaker diarization following SOLID principles
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import numpy as np


@dataclass
class SpeakerSegment:
    """Represents a segment spoken by one speaker"""
    speaker_id: str  # e.g., "SPEAKER_00", "SPEAKER_01"
    start: float  # Start time in seconds
    end: float  # End time in seconds
    confidence: float = 1.0


@dataclass
class DiarizationResult:
    """
    Complete diarization result
    """
    segments: List[SpeakerSegment]
    num_speakers: int
    duration: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_speaker_at_time(self, time: float) -> Optional[str]:
        """Get speaker ID at a specific time"""
        for segment in self.segments:
            if segment.start <= time <= segment.end:
                return segment.speaker_id
        return None

    def get_segments_for_speaker(self, speaker_id: str) -> List[SpeakerSegment]:
        """Get all segments for a specific speaker"""
        return [seg for seg in self.segments if seg.speaker_id == speaker_id]

    def get_speaker_durations(self) -> Dict[str, float]:
        """Get total speaking duration for each speaker"""
        durations = {}
        for segment in self.segments:
            if segment.speaker_id not in durations:
                durations[segment.speaker_id] = 0.0
            durations[segment.speaker_id] += (segment.end - segment.start)
        return durations


class DiarizationInterface(ABC):
    """
    Interface for speaker diarization (Interface Segregation Principle)
    """

    @abstractmethod
    def diarize(
        self,
        audio: np.ndarray,
        sample_rate: int,
        num_speakers: Optional[int] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None
    ) -> DiarizationResult:
        """
        Perform speaker diarization on audio

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            num_speakers: Exact number of speakers (if known)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers

        Returns:
            DiarizationResult: Diarization with speaker segments
        """
        pass

    @abstractmethod
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
        pass
