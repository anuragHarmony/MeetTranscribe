"""
Base interfaces for meeting bot integration
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


@dataclass
class ParticipantInfo:
    """Information about a meeting participant"""
    name: str
    email: Optional[str] = None
    participant_id: Optional[str] = None
    is_host: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MeetingMetadata:
    """Metadata about an online meeting"""
    meeting_id: str
    platform: str  # google_meet, zoom, teams, slack
    title: Optional[str] = None
    start_time: datetime = field(default_factory=datetime.now)
    participants: List[ParticipantInfo] = field(default_factory=list)
    meeting_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MeetingBotInterface(ABC):
    """
    Interface for meeting bot that joins online meetings
    """

    @abstractmethod
    def join_meeting(
        self,
        meeting_url: str,
        display_name: str = "MeetTranscribe Bot"
    ) -> MeetingMetadata:
        """
        Join an online meeting

        Args:
            meeting_url: URL to the meeting
            display_name: Display name for the bot

        Returns:
            MeetingMetadata: Meeting information
        """
        pass

    @abstractmethod
    def leave_meeting(self) -> None:
        """Leave the current meeting"""
        pass

    @abstractmethod
    def get_audio_stream(self):
        """
        Get audio stream from the meeting

        Returns:
            Generator yielding audio chunks
        """
        pass

    @abstractmethod
    def get_participants(self) -> List[ParticipantInfo]:
        """
        Get list of current participants

        Returns:
            List[ParticipantInfo]: Current participants
        """
        pass

    @abstractmethod
    def is_in_meeting(self) -> bool:
        """Check if currently in a meeting"""
        pass

    @abstractmethod
    def set_audio_callback(self, callback: Callable) -> None:
        """
        Set callback function for audio data

        Args:
            callback: Function to call with audio data
        """
        pass
