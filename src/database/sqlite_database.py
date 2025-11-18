"""
SQLite database implementation
"""

import sqlite3
from typing import Any, Optional
import logging
from pathlib import Path
from .base import DatabaseInterface

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseInterface):
    """
    SQLite database implementation for local storage
    """

    def __init__(self, db_path: str = "data/meettranscribe.db"):
        """
        Initialize SQLite database

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None

        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> None:
        """Establish database connection"""
        if self.connection is not None:
            return

        logger.info(f"Connecting to SQLite database: {self.db_path}")
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row  # Enable column access by name
        self.cursor = self.connection.cursor()

        # Initialize schema
        self._initialize_schema()

    def disconnect(self) -> None:
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.cursor = None
            logger.info("Database connection closed")

    def execute(self, query: str, params: tuple = ()) -> Any:
        """
        Execute a database query

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object with query results
        """
        if not self.cursor:
            self.connect()

        try:
            self.cursor.execute(query, params)
            return self.cursor
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise

    def commit(self) -> None:
        """Commit current transaction"""
        if self.connection:
            self.connection.commit()

    def rollback(self) -> None:
        """Rollback current transaction"""
        if self.connection:
            self.connection.rollback()

    def _initialize_schema(self) -> None:
        """Initialize database schema"""
        # Speakers table
        self.execute("""
            CREATE TABLE IF NOT EXISTS speakers (
                speaker_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Voice embeddings table
        self.execute("""
            CREATE TABLE IF NOT EXISTS voice_embeddings (
                embedding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                speaker_id TEXT NOT NULL,
                embedding BLOB NOT NULL,
                duration REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY (speaker_id) REFERENCES speakers(speaker_id)
                    ON DELETE CASCADE
            )
        """)

        # Create index on speaker_id for fast lookups
        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_speaker
            ON voice_embeddings(speaker_id)
        """)

        # Meetings table
        self.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                meeting_id TEXT PRIMARY KEY,
                title TEXT,
                platform TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                participants TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transcripts table
        self.execute("""
            CREATE TABLE IF NOT EXISTS transcripts (
                transcript_id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id TEXT NOT NULL,
                text TEXT NOT NULL,
                start_time REAL,
                end_time REAL,
                speaker_id TEXT,
                confidence REAL,
                metadata TEXT,
                FOREIGN KEY (meeting_id) REFERENCES meetings(meeting_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (speaker_id) REFERENCES speakers(speaker_id)
                    ON DELETE SET NULL
            )
        """)

        # Create index on meeting_id for fast lookups
        self.execute("""
            CREATE INDEX IF NOT EXISTS idx_transcripts_meeting
            ON transcripts(meeting_id)
        """)

        self.commit()
        logger.info("Database schema initialized")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.disconnect()
