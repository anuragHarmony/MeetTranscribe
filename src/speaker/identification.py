"""Speaker identification and voice embedding."""

import asyncio
import logging
from typing import List, Optional

import numpy as np
import torch
from speechbrain.pretrained import EncoderClassifier

from src.core.config import SpeakerRecognitionConfig
from src.core.interfaces import (
    AudioChunk,
    ISpeakerIdentification,
    IVoiceProfileStorage,
    VoiceProfile,
)

logger = logging.getLogger(__name__)


class SpeechBrainIdentification(ISpeakerIdentification):
    """Speaker identification using SpeechBrain embeddings."""

    def __init__(
        self,
        config: SpeakerRecognitionConfig,
        storage: IVoiceProfileStorage,
    ):
        """
        Initialize speaker identification.

        Args:
            config: Speaker recognition configuration
            storage: Voice profile storage
        """
        self.config = config
        self.storage = storage
        self.model: Optional[EncoderClassifier] = None
        self._is_initialized = False

    async def initialize(self) -> None:
        """Initialize speaker identification model."""
        if self._is_initialized:
            logger.warning("Speaker identification already initialized")
            return

        logger.info(f"Loading speaker embedding model: {self.config.embedding_model}")

        # Load model in thread pool
        loop = asyncio.get_event_loop()
        self.model = await loop.run_in_executor(
            None,
            self._load_model,
        )

        self._is_initialized = True
        logger.info("Speaker embedding model loaded")

    def _load_model(self) -> EncoderClassifier:
        """Load SpeechBrain model (runs in thread pool)."""
        model = EncoderClassifier.from_hparams(
            source=self.config.embedding_model,
            savedir=f"models/speaker_embedding",
            run_opts={"device": self.config.device},
        )
        return model

    async def extract_embedding(self, audio: AudioChunk) -> np.ndarray:
        """
        Extract voice embedding from audio.

        Args:
            audio: Audio chunk

        Returns:
            Voice embedding as numpy array
        """
        if not self._is_initialized or self.model is None:
            raise RuntimeError("Speaker identification not initialized")

        # Convert audio to float32 and normalize
        audio_data = audio.data.astype(np.float32)
        if audio_data.max() > 1.0:
            audio_data = audio_data / 32768.0

        # Ensure minimum duration (at least 1 second)
        min_samples = audio.sample_rate
        if len(audio_data) < min_samples:
            audio_data = np.pad(audio_data, (0, min_samples - len(audio_data)))

        # Run embedding extraction in thread pool
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            self._extract_embedding_sync,
            audio_data,
            audio.sample_rate,
        )

        return embedding

    def _extract_embedding_sync(
        self, audio_data: np.ndarray, sample_rate: int
    ) -> np.ndarray:
        """
        Synchronous embedding extraction (runs in thread pool).

        Args:
            audio_data: Audio data
            sample_rate: Sample rate

        Returns:
            Embedding vector
        """
        # Convert to tensor
        audio_tensor = torch.from_numpy(audio_data).float().unsqueeze(0)

        # Extract embedding
        with torch.no_grad():
            embedding = self.model.encode_batch(audio_tensor)
            embedding = embedding.squeeze().cpu().numpy()

        # Normalize embedding
        embedding = embedding / np.linalg.norm(embedding)

        return embedding

    async def identify_speaker(
        self, embedding: np.ndarray, threshold: float = None
    ) -> Optional[VoiceProfile]:
        """
        Identify speaker from voice embedding.

        Args:
            embedding: Voice embedding
            threshold: Similarity threshold (default from config)

        Returns:
            Matching voice profile or None
        """
        if threshold is None:
            threshold = self.config.similarity_threshold

        # Get all profiles
        profiles = await self.storage.get_all_profiles()

        if not profiles:
            logger.debug("No voice profiles available for identification")
            return None

        # Find best match
        best_match = None
        best_similarity = 0.0

        for profile in profiles:
            similarity = await self.compare_embeddings(embedding, profile.embedding)

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = profile

        # Return match if above threshold
        if best_similarity >= threshold:
            logger.info(
                f"Identified speaker: {best_match.name} "
                f"(similarity: {best_similarity:.3f})"
            )
            return best_match
        else:
            logger.debug(
                f"No match found (best similarity: {best_similarity:.3f}, "
                f"threshold: {threshold:.3f})"
            )
            return None

    async def compare_embeddings(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        Compare two voice embeddings using cosine similarity.

        Args:
            embedding1: First embedding
            embedding2: Second embedding

        Returns:
            Similarity score [0, 1]
        """
        # Ensure embeddings are normalized
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2)

        # Convert to [0, 1] range (cosine similarity is [-1, 1])
        similarity = (similarity + 1) / 2

        return float(similarity)

    async def update_profile_with_new_sample(
        self, profile: VoiceProfile, new_embedding: np.ndarray
    ) -> np.ndarray:
        """
        Update profile embedding with new sample using incremental learning.

        Args:
            profile: Existing voice profile
            new_embedding: New embedding to incorporate

        Returns:
            Updated embedding
        """
        # Weighted average: more weight to existing profile
        weight_new = self.config.embedding_update_weight
        weight_old = 1.0 - weight_new

        updated_embedding = (
            weight_old * profile.embedding + weight_new * new_embedding
        )

        # Normalize
        updated_embedding = updated_embedding / np.linalg.norm(updated_embedding)

        return updated_embedding
