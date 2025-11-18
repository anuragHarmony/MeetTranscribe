"""
WeSpeaker implementation for voice recognition using ECAPA-TDNN embeddings
"""

import numpy as np
from typing import List, Tuple
import logging
import tempfile
import soundfile as sf
from pathlib import Path

from .base import (
    VoiceRecognitionInterface,
    VoiceEmbedding,
    SpeakerProfile,
    RecognitionResult
)

try:
    import wespeaker
except ImportError:
    wespeaker = None

logger = logging.getLogger(__name__)


class WeSpeakerRecognizer(VoiceRecognitionInterface):
    """
    Voice recognition using WeSpeaker with ECAPA-TDNN embeddings

    WeSpeaker provides:
    - High-quality speaker embeddings
    - Fast inference
    - Pre-trained on large-scale datasets
    - Support for multiple languages
    """

    def __init__(
        self,
        model_name: str = "wespeaker-voxceleb-resnet34-LM",
        device: str = "auto"
    ):
        """
        Initialize WeSpeaker recognizer

        Args:
            model_name: Pre-trained model name
                       - "wespeaker-voxceleb-resnet34-LM" (ResNet-based)
                       - "wespeaker-voxceleb-ecapa-tdnn-LM" (ECAPA-TDNN, recommended)
            device: Device to use (cpu, cuda, auto)
        """
        if wespeaker is None:
            raise ImportError(
                "wespeaker is not installed. "
                "Install it with: pip install wespeaker"
            )

        self.model_name = model_name
        self.device = self._determine_device(device)

        logger.info(f"Initializing WeSpeaker: {model_name} on {self.device}")

        # Load WeSpeaker model
        try:
            self.model = wespeaker.load_model(model_name)
            if self.device == "cuda":
                self.model = self.model.cuda()
        except Exception as e:
            logger.error(f"Failed to load WeSpeaker model: {e}")
            raise

    def _determine_device(self, device: str) -> str:
        """Determine best device to use"""
        if device != "auto":
            return device

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def extract_embedding(
        self,
        audio: np.ndarray,
        sample_rate: int
    ) -> VoiceEmbedding:
        """
        Extract voice embedding from audio using WeSpeaker

        Args:
            audio: Audio data as numpy array (mono, float32)
            sample_rate: Sample rate in Hz

        Returns:
            VoiceEmbedding: Voice embedding vector
        """
        # Ensure audio is float32 and mono
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if audio.ndim > 1:
            audio = audio.mean(axis=1)

        # WeSpeaker expects 16kHz audio
        if sample_rate != 16000:
            logger.warning(f"Resampling from {sample_rate}Hz to 16000Hz")
            import librosa
            audio = librosa.resample(
                audio,
                orig_sr=sample_rate,
                target_sr=16000
            )
            sample_rate = 16000

        # WeSpeaker works with audio files, so save temporarily
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            sf.write(tmp_path, audio, sample_rate)

        try:
            # Extract embedding
            embedding_vector = self.model.extract_embedding(tmp_path)

            # Convert to numpy if tensor
            if hasattr(embedding_vector, 'cpu'):
                embedding_vector = embedding_vector.cpu().numpy()

            # Ensure 1D array
            if embedding_vector.ndim > 1:
                embedding_vector = embedding_vector.squeeze()

            duration = len(audio) / sample_rate

            return VoiceEmbedding(
                embedding=embedding_vector,
                duration=duration,
                metadata={
                    "model": self.model_name,
                    "sample_rate": sample_rate
                }
            )

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compute cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Similarity score [0, 1]
        """
        # Normalize embeddings
        emb1_norm = embedding1 / np.linalg.norm(embedding1)
        emb2_norm = embedding2 / np.linalg.norm(embedding2)

        # Cosine similarity
        similarity = np.dot(emb1_norm, emb2_norm)

        # Convert to [0, 1] range
        similarity = (similarity + 1) / 2

        return float(similarity)

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
            threshold: Minimum similarity threshold

        Returns:
            RecognitionResult: Recognition result
        """
        # Extract embedding from audio
        voice_emb = self.extract_embedding(audio, sample_rate)
        query_embedding = voice_emb.embedding

        # Compare against all speaker profiles
        matches: List[Tuple[str, float]] = []

        for profile in speaker_profiles:
            # Get average embedding for this speaker
            avg_embedding = profile.get_average_embedding()
            if avg_embedding is None:
                continue

            # Compute similarity
            similarity = self.compute_similarity(query_embedding, avg_embedding)
            matches.append((profile.speaker_id, similarity))

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        # Determine best match
        if matches and matches[0][1] >= threshold:
            best_speaker_id, best_score = matches[0]
            return RecognitionResult(
                speaker_id=best_speaker_id,
                confidence=best_score,
                similarity_score=best_score,
                all_matches=matches,
                is_new_speaker=False
            )
        else:
            # Unknown speaker
            return RecognitionResult(
                speaker_id=None,
                confidence=matches[0][1] if matches else 0.0,
                similarity_score=matches[0][1] if matches else 0.0,
                all_matches=matches,
                is_new_speaker=True
            )

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
            bool: True if verified
        """
        # Extract embedding
        voice_emb = self.extract_embedding(audio, sample_rate)

        # Get average embedding for speaker
        avg_embedding = speaker_profile.get_average_embedding()
        if avg_embedding is None:
            return False

        # Compute similarity
        similarity = self.compute_similarity(voice_emb.embedding, avg_embedding)

        return similarity >= threshold

    def extract_embedding_from_file(self, audio_path: str) -> VoiceEmbedding:
        """
        Extract embedding directly from audio file

        Args:
            audio_path: Path to audio file

        Returns:
            VoiceEmbedding: Voice embedding
        """
        # Load audio
        audio, sample_rate = sf.read(audio_path, dtype='float32')

        return self.extract_embedding(audio, sample_rate)
