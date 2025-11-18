"""
Database layer for speaker persistence and meeting records
"""

from .base import DatabaseInterface
from .sqlite_database import SQLiteDatabase
from .speaker_repository import SpeakerRepository
from .meeting_repository import MeetingRepository

__all__ = [
    "DatabaseInterface",
    "SQLiteDatabase",
    "SpeakerRepository",
    "MeetingRepository"
]
