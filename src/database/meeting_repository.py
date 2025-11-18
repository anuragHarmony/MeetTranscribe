"""
Repository for meeting and transcript persistence
"""

import json
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from dataclasses import dataclass, field

from .base import RepositoryInterface, DatabaseInterface
from ..transcription.base import Segment

logger = logging.getLogger(__name__)


@dataclass
class Meeting:
    """Meeting record"""
    meeting_id: str
    title: str
    platform: str  # google_meet, zoom, teams, local
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: float = 0.0
    participants: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Transcript:
    """Transcript segment"""
    transcript_id: Optional[int]
    meeting_id: str
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class MeetingRepository(RepositoryInterface):
    """
    Repository for managing meeting records and transcripts
    """

    def __init__(self, database: DatabaseInterface):
        """
        Initialize meeting repository

        Args:
            database: Database instance
        """
        self.db = database

    def create(self, entity: Meeting) -> str:
        """
        Create a new meeting record

        Args:
            entity: Meeting to create

        Returns:
            str: Meeting ID
        """
        participants_json = json.dumps(entity.participants)
        metadata_json = json.dumps(entity.metadata)

        self.db.execute(
            """
            INSERT INTO meetings
            (meeting_id, title, platform, start_time, end_time, duration,
             participants, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entity.meeting_id,
                entity.title,
                entity.platform,
                entity.start_time.isoformat(),
                entity.end_time.isoformat() if entity.end_time else None,
                entity.duration,
                participants_json,
                metadata_json,
                entity.created_at.isoformat()
            )
        )

        self.db.commit()
        logger.info(f"Created meeting record: {entity.meeting_id}")

        return entity.meeting_id

    def get(self, entity_id: str) -> Optional[Meeting]:
        """
        Get meeting by ID

        Args:
            entity_id: Meeting ID

        Returns:
            Optional[Meeting]: Meeting record or None
        """
        cursor = self.db.execute(
            "SELECT * FROM meetings WHERE meeting_id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        participants = json.loads(row["participants"]) if row["participants"] else []
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        meeting = Meeting(
            meeting_id=row["meeting_id"],
            title=row["title"],
            platform=row["platform"],
            start_time=datetime.fromisoformat(row["start_time"]),
            end_time=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
            duration=row["duration"],
            participants=participants,
            metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"])
        )

        return meeting

    def update(self, entity: Meeting) -> bool:
        """
        Update existing meeting

        Args:
            entity: Meeting to update

        Returns:
            bool: True if updated successfully
        """
        participants_json = json.dumps(entity.participants)
        metadata_json = json.dumps(entity.metadata)

        cursor = self.db.execute(
            """
            UPDATE meetings
            SET title = ?, platform = ?, start_time = ?, end_time = ?,
                duration = ?, participants = ?, metadata = ?
            WHERE meeting_id = ?
            """,
            (
                entity.title,
                entity.platform,
                entity.start_time.isoformat(),
                entity.end_time.isoformat() if entity.end_time else None,
                entity.duration,
                participants_json,
                metadata_json,
                entity.meeting_id
            )
        )

        self.db.commit()
        return cursor.rowcount > 0

    def delete(self, entity_id: str) -> bool:
        """
        Delete meeting

        Args:
            entity_id: Meeting ID

        Returns:
            bool: True if deleted successfully
        """
        cursor = self.db.execute(
            "DELETE FROM meetings WHERE meeting_id = ?",
            (entity_id,)
        )
        self.db.commit()

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted meeting: {entity_id}")

        return deleted

    def list_all(self) -> List[Meeting]:
        """
        List all meetings

        Returns:
            List[Meeting]: All meetings
        """
        cursor = self.db.execute(
            "SELECT meeting_id FROM meetings ORDER BY start_time DESC"
        )
        rows = cursor.fetchall()

        meetings = []
        for row in rows:
            meeting = self.get(row["meeting_id"])
            if meeting:
                meetings.append(meeting)

        return meetings

    def add_transcript(self, transcript: Transcript) -> int:
        """
        Add transcript segment to meeting

        Args:
            transcript: Transcript segment

        Returns:
            int: Transcript ID
        """
        metadata_json = json.dumps(transcript.metadata)

        cursor = self.db.execute(
            """
            INSERT INTO transcripts
            (meeting_id, text, start_time, end_time, speaker_id, confidence, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transcript.meeting_id,
                transcript.text,
                transcript.start_time,
                transcript.end_time,
                transcript.speaker_id,
                transcript.confidence,
                metadata_json
            )
        )

        self.db.commit()
        return cursor.lastrowid

    def get_transcripts(self, meeting_id: str) -> List[Transcript]:
        """
        Get all transcripts for a meeting

        Args:
            meeting_id: Meeting ID

        Returns:
            List[Transcript]: Transcript segments
        """
        cursor = self.db.execute(
            """
            SELECT * FROM transcripts
            WHERE meeting_id = ?
            ORDER BY start_time ASC
            """,
            (meeting_id,)
        )

        transcripts = []
        for row in cursor.fetchall():
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            transcript = Transcript(
                transcript_id=row["transcript_id"],
                meeting_id=row["meeting_id"],
                text=row["text"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                speaker_id=row["speaker_id"],
                confidence=row["confidence"],
                metadata=metadata
            )
            transcripts.append(transcript)

        return transcripts

    def get_full_transcript_text(self, meeting_id: str) -> str:
        """
        Get full transcript as formatted text

        Args:
            meeting_id: Meeting ID

        Returns:
            str: Formatted transcript text
        """
        transcripts = self.get_transcripts(meeting_id)

        lines = []
        for t in transcripts:
            speaker = t.speaker_id or "Unknown"
            timestamp = self._format_timestamp(t.start_time)
            lines.append(f"[{timestamp}] {speaker}: {t.text}")

        return "\n".join(lines)

    def search_transcripts(self, query: str) -> List[Transcript]:
        """
        Search transcripts by text content

        Args:
            query: Search query

        Returns:
            List[Transcript]: Matching transcripts
        """
        cursor = self.db.execute(
            """
            SELECT * FROM transcripts
            WHERE text LIKE ?
            ORDER BY meeting_id, start_time
            """,
            (f"%{query}%",)
        )

        transcripts = []
        for row in cursor.fetchall():
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            transcript = Transcript(
                transcript_id=row["transcript_id"],
                meeting_id=row["meeting_id"],
                text=row["text"],
                start_time=row["start_time"],
                end_time=row["end_time"],
                speaker_id=row["speaker_id"],
                confidence=row["confidence"],
                metadata=metadata
            )
            transcripts.append(transcript)

        return transcripts

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """Format timestamp as HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
