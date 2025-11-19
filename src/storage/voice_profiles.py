"""Voice profile storage implementation."""

import asyncio
import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker

from src.core.config import StorageConfig
from src.core.interfaces import IVoiceProfileStorage, VoiceProfile

logger = logging.getLogger(__name__)

Base = declarative_base()


class VoiceProfileModel(Base):
    """SQLAlchemy model for voice profiles."""

    __tablename__ = "voice_profiles"

    id = Column(Integer, primary_key=True)
    profile_id = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    email = Column(String(255), index=True)
    embedding_path = Column(String(512))  # Path to embedding file
    sample_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata_json = Column(Text)  # JSON-serialized metadata


class VoiceProfileStorage(IVoiceProfileStorage):
    """File and database-based voice profile storage."""

    def __init__(self, config: StorageConfig):
        """
        Initialize voice profile storage.

        Args:
            config: Storage configuration
        """
        self.config = config
        self.embeddings_dir = Path(config.voice_profiles_path)
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)

        # Setup database
        # Convert sqlite:/// to sqlite+aiosqlite:///
        db_url = config.database_url
        if db_url.startswith("sqlite:///"):
            db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")

        self.engine = create_async_engine(db_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize storage (create tables)."""
        if self._is_initialized:
            return

        logger.info("Initializing voice profile storage")

        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self._is_initialized = True
        logger.info("Voice profile storage initialized")

    async def save_profile(self, profile: VoiceProfile) -> None:
        """
        Save or update voice profile.

        Args:
            profile: Voice profile to save
        """
        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Saving voice profile: {profile.profile_id}")

        # Save embedding to file
        embedding_path = self.embeddings_dir / f"{profile.profile_id}.npy"
        await asyncio.get_event_loop().run_in_executor(
            None, np.save, str(embedding_path), profile.embedding
        )

        # Save metadata to database
        async with self.async_session() as session:
            # Check if profile exists
            result = await session.execute(
                select(VoiceProfileModel).where(
                    VoiceProfileModel.profile_id == profile.profile_id
                )
            )
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing profile
                existing.name = profile.name
                existing.email = profile.email
                existing.embedding_path = str(embedding_path)
                existing.sample_count = profile.sample_count
                existing.updated_at = profile.updated_at
                existing.metadata_json = (
                    json.dumps(profile.metadata) if profile.metadata else None
                )
            else:
                # Create new profile
                new_profile = VoiceProfileModel(
                    profile_id=profile.profile_id,
                    name=profile.name,
                    email=profile.email,
                    embedding_path=str(embedding_path),
                    sample_count=profile.sample_count,
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                    metadata_json=(
                        json.dumps(profile.metadata) if profile.metadata else None
                    ),
                )
                session.add(new_profile)

            await session.commit()

        logger.info(f"Voice profile saved: {profile.profile_id}")

    async def get_profile(self, profile_id: str) -> Optional[VoiceProfile]:
        """
        Get voice profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            Voice profile or None
        """
        if not self._is_initialized:
            await self.initialize()

        async with self.async_session() as session:
            result = await session.execute(
                select(VoiceProfileModel).where(
                    VoiceProfileModel.profile_id == profile_id
                )
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            # Load embedding
            embedding = await asyncio.get_event_loop().run_in_executor(
                None, np.load, model.embedding_path
            )

            # Convert to VoiceProfile
            profile = VoiceProfile(
                profile_id=model.profile_id,
                name=model.name,
                email=model.email,
                embedding=embedding,
                sample_count=model.sample_count,
                created_at=model.created_at,
                updated_at=model.updated_at,
                metadata=(
                    json.loads(model.metadata_json) if model.metadata_json else None
                ),
            )

            return profile

    async def get_profile_by_email(self, email: str) -> Optional[VoiceProfile]:
        """
        Get voice profile by email.

        Args:
            email: Email address

        Returns:
            Voice profile or None
        """
        if not self._is_initialized:
            await self.initialize()

        async with self.async_session() as session:
            result = await session.execute(
                select(VoiceProfileModel).where(VoiceProfileModel.email == email)
            )
            model = result.scalar_one_or_none()

            if model is None:
                return None

            # Load embedding
            embedding = await asyncio.get_event_loop().run_in_executor(
                None, np.load, model.embedding_path
            )

            # Convert to VoiceProfile
            profile = VoiceProfile(
                profile_id=model.profile_id,
                name=model.name,
                email=model.email,
                embedding=embedding,
                sample_count=model.sample_count,
                created_at=model.created_at,
                updated_at=model.updated_at,
                metadata=(
                    json.loads(model.metadata_json) if model.metadata_json else None
                ),
            )

            return profile

    async def get_all_profiles(self) -> List[VoiceProfile]:
        """
        Get all voice profiles.

        Returns:
            List of voice profiles
        """
        if not self._is_initialized:
            await self.initialize()

        async with self.async_session() as session:
            result = await session.execute(select(VoiceProfileModel))
            models = result.scalars().all()

            profiles = []
            for model in models:
                try:
                    # Load embedding
                    embedding = await asyncio.get_event_loop().run_in_executor(
                        None, np.load, model.embedding_path
                    )

                    profile = VoiceProfile(
                        profile_id=model.profile_id,
                        name=model.name,
                        email=model.email,
                        embedding=embedding,
                        sample_count=model.sample_count,
                        created_at=model.created_at,
                        updated_at=model.updated_at,
                        metadata=(
                            json.loads(model.metadata_json)
                            if model.metadata_json
                            else None
                        ),
                    )
                    profiles.append(profile)
                except Exception as e:
                    logger.error(f"Error loading profile {model.profile_id}: {e}")

            return profiles

    async def update_profile_embedding(
        self, profile_id: str, new_embedding: np.ndarray
    ) -> None:
        """
        Update profile embedding (incremental learning).

        Args:
            profile_id: Profile ID
            new_embedding: New embedding
        """
        profile = await self.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"Profile not found: {profile_id}")

        # Update embedding
        profile.embedding = new_embedding
        profile.sample_count += 1
        profile.updated_at = datetime.utcnow()

        # Save
        await self.save_profile(profile)

    async def delete_profile(self, profile_id: str) -> None:
        """
        Delete voice profile.

        Args:
            profile_id: Profile ID
        """
        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Deleting voice profile: {profile_id}")

        # Delete from database
        async with self.async_session() as session:
            result = await session.execute(
                select(VoiceProfileModel).where(
                    VoiceProfileModel.profile_id == profile_id
                )
            )
            model = result.scalar_one_or_none()

            if model:
                # Delete embedding file
                embedding_path = Path(model.embedding_path)
                if embedding_path.exists():
                    await asyncio.get_event_loop().run_in_executor(
                        None, embedding_path.unlink
                    )

                # Delete from database
                await session.delete(model)
                await session.commit()

        logger.info(f"Voice profile deleted: {profile_id}")
