"""
Repository for speaker profile persistence
"""

import json
import pickle
import numpy as np
from typing import List, Optional
import logging
from datetime import datetime

from .base import RepositoryInterface, DatabaseInterface
from ..voice_recognition.base import SpeakerProfile, VoiceEmbedding

logger = logging.getLogger(__name__)


class SpeakerRepository(RepositoryInterface):
    """
    Repository for managing speaker profiles in database
    Implements Repository Pattern for separation of concerns
    """

    def __init__(self, database: DatabaseInterface):
        """
        Initialize speaker repository

        Args:
            database: Database instance
        """
        self.db = database

    def create(self, entity: SpeakerProfile) -> str:
        """
        Create a new speaker profile

        Args:
            entity: SpeakerProfile to create

        Returns:
            str: Speaker ID
        """
        # Insert speaker
        metadata_json = json.dumps(entity.metadata)

        self.db.execute(
            """
            INSERT INTO speakers (speaker_id, name, email, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                entity.speaker_id,
                entity.name,
                entity.email,
                metadata_json,
                entity.created_at.isoformat(),
                entity.updated_at.isoformat()
            )
        )

        # Insert embeddings
        for embedding in entity.embeddings:
            self._save_embedding(entity.speaker_id, embedding)

        self.db.commit()
        logger.info(f"Created speaker profile: {entity.speaker_id}")

        return entity.speaker_id

    def get(self, entity_id: str) -> Optional[SpeakerProfile]:
        """
        Get speaker profile by ID

        Args:
            entity_id: Speaker ID

        Returns:
            Optional[SpeakerProfile]: Speaker profile or None
        """
        cursor = self.db.execute(
            "SELECT * FROM speakers WHERE speaker_id = ?",
            (entity_id,)
        )
        row = cursor.fetchone()

        if not row:
            return None

        # Load embeddings
        embeddings = self._load_embeddings(entity_id)

        # Parse metadata
        metadata = json.loads(row["metadata"]) if row["metadata"] else {}

        profile = SpeakerProfile(
            speaker_id=row["speaker_id"],
            name=row["name"],
            email=row["email"],
            embeddings=embeddings,
            metadata=metadata,
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )

        return profile

    def update(self, entity: SpeakerProfile) -> bool:
        """
        Update existing speaker profile

        Args:
            entity: SpeakerProfile to update

        Returns:
            bool: True if updated successfully
        """
        metadata_json = json.dumps(entity.metadata)
        entity.updated_at = datetime.now()

        cursor = self.db.execute(
            """
            UPDATE speakers
            SET name = ?, email = ?, metadata = ?, updated_at = ?
            WHERE speaker_id = ?
            """,
            (
                entity.name,
                entity.email,
                metadata_json,
                entity.updated_at.isoformat(),
                entity.speaker_id
            )
        )

        # Delete old embeddings and insert new ones
        self.db.execute(
            "DELETE FROM voice_embeddings WHERE speaker_id = ?",
            (entity.speaker_id,)
        )

        for embedding in entity.embeddings:
            self._save_embedding(entity.speaker_id, embedding)

        self.db.commit()

        return cursor.rowcount > 0

    def delete(self, entity_id: str) -> bool:
        """
        Delete speaker profile

        Args:
            entity_id: Speaker ID

        Returns:
            bool: True if deleted successfully
        """
        cursor = self.db.execute(
            "DELETE FROM speakers WHERE speaker_id = ?",
            (entity_id,)
        )
        self.db.commit()

        deleted = cursor.rowcount > 0
        if deleted:
            logger.info(f"Deleted speaker profile: {entity_id}")

        return deleted

    def list_all(self) -> List[SpeakerProfile]:
        """
        List all speaker profiles

        Returns:
            List[SpeakerProfile]: All speaker profiles
        """
        cursor = self.db.execute("SELECT speaker_id FROM speakers")
        rows = cursor.fetchall()

        profiles = []
        for row in rows:
            profile = self.get(row["speaker_id"])
            if profile:
                profiles.append(profile)

        return profiles

    def find_by_email(self, email: str) -> Optional[SpeakerProfile]:
        """
        Find speaker by email

        Args:
            email: Email address

        Returns:
            Optional[SpeakerProfile]: Speaker profile or None
        """
        cursor = self.db.execute(
            "SELECT speaker_id FROM speakers WHERE email = ?",
            (email,)
        )
        row = cursor.fetchone()

        if row:
            return self.get(row["speaker_id"])

        return None

    def add_embedding(self, speaker_id: str, embedding: VoiceEmbedding) -> bool:
        """
        Add a new voice embedding to existing speaker

        Args:
            speaker_id: Speaker ID
            embedding: Voice embedding to add

        Returns:
            bool: True if added successfully
        """
        profile = self.get(speaker_id)
        if not profile:
            return False

        self._save_embedding(speaker_id, embedding)

        # Update timestamp
        self.db.execute(
            "UPDATE speakers SET updated_at = ? WHERE speaker_id = ?",
            (datetime.now().isoformat(), speaker_id)
        )

        self.db.commit()
        return True

    def _save_embedding(self, speaker_id: str, embedding: VoiceEmbedding) -> None:
        """Save voice embedding to database"""
        # Serialize embedding array
        embedding_blob = pickle.dumps(embedding.embedding)
        metadata_json = json.dumps(embedding.metadata)

        self.db.execute(
            """
            INSERT INTO voice_embeddings
            (speaker_id, embedding, duration, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                speaker_id,
                embedding_blob,
                embedding.duration,
                embedding.timestamp.isoformat(),
                metadata_json
            )
        )

    def _load_embeddings(self, speaker_id: str) -> List[VoiceEmbedding]:
        """Load all voice embeddings for a speaker"""
        cursor = self.db.execute(
            """
            SELECT embedding, duration, timestamp, metadata
            FROM voice_embeddings
            WHERE speaker_id = ?
            ORDER BY timestamp DESC
            """,
            (speaker_id,)
        )

        embeddings = []
        for row in cursor.fetchall():
            # Deserialize embedding array
            embedding_array = pickle.loads(row["embedding"])
            metadata = json.loads(row["metadata"]) if row["metadata"] else {}

            emb = VoiceEmbedding(
                embedding=embedding_array,
                timestamp=datetime.fromisoformat(row["timestamp"]),
                duration=row["duration"],
                metadata=metadata
            )
            embeddings.append(emb)

        return embeddings
