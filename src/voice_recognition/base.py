"""
Base interfaces for voice recognition and speaker identification
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from datetime import datetime


@dataclass
class VoiceEmbedding:
    """
    Voice embedding representation for a speaker
    """
    embedding: np.ndarray  # High-dimensional vector representation
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0  # Duration of audio used for embedding
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpeakerProfile:
    """
    Complete profile for a known speaker with persistent identity
    """
    speaker_id: str  # Unique identifier (e.g., email, employee_id)
    name: str
    email: Optional[str] = None
    embeddings: List[VoiceEmbedding] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def get_average_embedding(self) -> Optional[np.ndarray]:
        """Get average embedding across all samples"""
        if not self.embeddings:
            return None

        embeddings_array = np.array([emb.embedding for emb in self.embeddings])
        return np.mean(embeddings_array, axis=0)

    def add_embedding(self, embedding: VoiceEmbedding):
        """Add a new voice embedding sample"""
        self.embeddings.append(embedding)
        self.updated_at = datetime.now()


@dataclass
class RecognitionResult:
    """Result of speaker recognition"""
    speaker_id: Optional[str]  # Identified speaker ID or None if unknown
    confidence: float  # Confidence score [0, 1]
    similarity_score: float  # Similarity to best match
    all_matches: List[Tuple[str, float]] = field(default_factory=list)  # All candidates with scores
    is_new_speaker: bool = False


class VoiceRecognitionInterface(ABC):
    """
    Interface for voice recognition and speaker identification
    """

    @abstractmethod
    def extract_embedding(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> VoiceEmbedding:
        """
        Extract voice embedding from audio

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz

        Returns:
            VoiceEmbedding: Voice embedding vector
        """
        pass

    @abstractmethod
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Similarity score [0, 1] where 1 is identical
        """
        pass

    @abstractmethod
    def recognize_speaker(
        self,
        audio: np.ndarray,
        sample_rate: int,
        speaker_profiles: List[SpeakerProfile],
        threshold: float = 0.7
    ) -> RecognitionResult:
        """
        Recognize speaker from audio against known profiles

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            speaker_profiles: List of known speaker profiles
            threshold: Minimum similarity threshold for recognition

        Returns:
            RecognitionResult: Recognition result with best match
        """
        pass

    @abstractmethod
    def verify_speaker(
        self,
        audio: np.ndarray,
        sample_rate: int,
        speaker_profile: SpeakerProfile,
        threshold: float = 0.7
    ) -> bool:
        """
        Verify if audio belongs to a specific speaker

        Args:
            audio: Audio data as numpy array
            sample_rate: Sample rate in Hz
            speaker_profile: Speaker profile to verify against
            threshold: Minimum similarity threshold

        Returns:
            bool: True if verified, False otherwise
        """
        pass
