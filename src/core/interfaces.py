"""Core interfaces following SOLID principles."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional

import numpy as np


class AudioSource(str, Enum):
    """Audio source types."""
    LOCAL_MIC = "local_mic"
    SYSTEM_AUDIO = "system_audio"
    ONLINE_MEETING = "online_meeting"
    COMBINED = "combined"


class MeetingPlatform(str, Enum):
    """Supported meeting platforms."""
    GOOGLE_MEET = "google_meet"
    ZOOM = "zoom"
    MICROSOFT_TEAMS = "microsoft_teams"
    SLACK_HUDDLE = "slack_huddle"
    LOCAL = "local"


@dataclass
class AudioChunk:
    """Represents a chunk of audio data."""
    data: np.ndarray
    sample_rate: int
    timestamp: datetime
    source: AudioSource
    duration_ms: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TranscriptionSegment:
    """Represents a transcribed segment of audio."""
    text: str
    start_time: float
    end_time: float
    confidence: float
    language: Optional[str] = None
    speaker_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SpeakerSegment:
    """Represents a speaker diarization segment."""
    speaker_id: str
    start_time: float
    end_time: float
    confidence: float


@dataclass
class VoiceProfile:
    """Represents a speaker's voice profile."""
    profile_id: str
    name: Optional[str]
    email: Optional[str]
    embedding: np.ndarray
    sample_count: int
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MeetingMetadata:
    """Meeting metadata."""
    meeting_id: str
    platform: MeetingPlatform
    title: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    participants: List[Dict[str, str]]
    metadata: Optional[Dict[str, Any]] = None


class IAudioCapture(ABC):
    """Interface for audio capture implementations."""

    @abstractmethod
    async def start(self) -> None:
        """Start capturing audio."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop capturing audio."""
        pass

    @abstractmethod
    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get stream of audio chunks."""
        pass

    @abstractmethod
    def is_active(self) -> bool:
        """Check if capture is active."""
        pass


class ITranscriptionEngine(ABC):
    """Interface for transcription engines."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the transcription engine."""
        pass

    @abstractmethod
    async def transcribe(self, audio: AudioChunk) -> List[TranscriptionSegment]:
        """Transcribe audio chunk."""
        pass

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[TranscriptionSegment]:
        """Transcribe audio stream in real-time."""
        pass


class ISpeakerDiarization(ABC):
    """Interface for speaker diarization."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the diarization engine."""
        pass

    @abstractmethod
    async def diarize(self, audio: AudioChunk) -> List[SpeakerSegment]:
        """Perform speaker diarization on audio."""
        pass


class ISpeakerIdentification(ABC):
    """Interface for speaker identification."""

    @abstractmethod
    async def extract_embedding(self, audio: AudioChunk) -> np.ndarray:
        """Extract voice embedding from audio."""
        pass

    @abstractmethod
    async def identify_speaker(
        self, embedding: np.ndarray, threshold: float = 0.85
    ) -> Optional[VoiceProfile]:
        """Identify speaker from voice embedding."""
        pass

    @abstractmethod
    async def compare_embeddings(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """Compare two voice embeddings. Returns similarity score [0, 1]."""
        pass


class IVoiceProfileStorage(ABC):
    """Interface for voice profile storage."""

    @abstractmethod
    async def save_profile(self, profile: VoiceProfile) -> None:
        """Save or update voice profile."""
        pass

    @abstractmethod
    async def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """Get voice profile by ID."""
        pass

    @abstractmethod
    async def get_profile_by_email(self, email: str) -> Optional[VoiceProfile]:
        """Get voice profile by email."""
        pass

    @abstractmethod
    async def get_all_profiles(self) -> List[VoiceProfile]:
        """Get all voice profiles."""
        pass

    @abstractmethod
    async def update_profile_embedding(
        self, profile_id: str, new_embedding: np.ndarray
    ) -> None:
        """Update profile embedding (incremental learning)."""
        pass

    @abstractmethod
    async def delete_profile(self, profile_id: str) -> None:
        """Delete voice profile."""
        pass


class IMeetingPlatformIntegration(ABC):
    """Interface for meeting platform integrations."""

    @abstractmethod
    async def connect(self, meeting_url: str, credentials: Optional[Dict[str, str]] = None) -> None:
        """Connect to a meeting."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from meeting."""
        pass

    @abstractmethod
    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get audio stream from meeting."""
        pass

    @abstractmethod
    async def get_metadata(self) -> MeetingMetadata:
        """Get meeting metadata."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to meeting."""
        pass


class IMetadataExtractor(ABC):
    """Interface for metadata extraction."""

    @abstractmethod
    async def extract_participants(self, platform: MeetingPlatform) -> List[Dict[str, str]]:
        """Extract participant information."""
        pass

    @abstractmethod
    async def extract_meeting_info(self, platform: MeetingPlatform) -> Dict[str, Any]:
        """Extract meeting information."""
        pass
