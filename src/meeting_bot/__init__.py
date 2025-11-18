"""
Meeting bot integration for joining online meetings
"""

from .base import MeetingBotInterface, MeetingMetadata
from .playwright_bot import PlaywrightMeetingBot

__all__ = [
    "MeetingBotInterface",
    "MeetingMetadata",
    "PlaywrightMeetingBot"
]
