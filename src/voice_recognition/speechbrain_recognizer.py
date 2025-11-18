"""
SpeechBrain implementation for voice recognition using ECAPA-TDNN embeddings
Alternative to WeSpeaker with different pre-trained models
"""

import numpy as np
from typing import List, Tuple
import logging
import tempfile
import soundfile as sf
from pathlib import Path
import torch

from .base import (
    VoiceRecognitionInterface,
    VoiceEmbedding,
    SpeakerProfile,
    RecognitionResult
)

try:
    from speechbrain.pretrained import EncoderClassifier
except ImportError:
    EncoderClassifier = None

logger = logging.getLogger(__name__)


class SpeechBrainRecognizer(VoiceRecognitionInterface):
    """
    Voice recognition using SpeechBrain with ECAPA-TDNN embeddings

    SpeechBrain provides:
    - State-of-the-art ECAPA-TDNN models
    - Pre-trained on VoxCeleb datasets
    - Easy-to-use interface
    - Excellent speaker verification performance
    """

    def __init__(
        self,
        model_source: str = "speechbrain/spkrec-ecapa-voxceleb",
        device: str = "auto"
    ):
        """
        Initialize SpeechBrain recognizer

        Args:
            model_source: HuggingFace model identifier
                         - "speechbrain/spkrec-ecapa-voxceleb" (recommended)
                         - "speechbrain/spkrec-xvect-voxceleb"
            device: Device to use (cpu, cuda, auto)
        """
        if EncoderClassifier is None:
            raise ImportError(
                "speechbrain is not installed. "
                "Install it with: pip install speechbrain"
            )

        self.model_source = model_source
        self.device = self._determine_device(device)

        logger.info(f"Initializing SpeechBrain: {model_source} on {self.device}")

        # Load SpeechBrain model
        try:
            self.model = EncoderClassifier.from_hparams(
                source=model_source,
                savedir=f"data/models/speechbrain/{model_source.split('/')[-1]}",
                run_opts={"device": self.device}
            )
        except Exception as e:
            logger.error(f"Failed to load SpeechBrain model: {e}")
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
        Extract voice embedding from audio using SpeechBrain

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

        # SpeechBrain expects 16kHz audio
        if sample_rate != 16000:
            logger.warning(f"Resampling from {sample_rate}Hz to 16000Hz")
            import torchaudio.transforms as T
            resampler = T.Resample(sample_rate, 16000)
            audio_tensor = torch.from_numpy(audio)
            audio = resampler(audio_tensor).numpy()
            sample_rate = 16000

        # Convert to tensor
        audio_tensor = torch.from_numpy(audio).unsqueeze(0)

        # Move to device
        if self.device == "cuda":
            audio_tensor = audio_tensor.cuda()

        # Extract embedding
        with torch.no_grad():
            embedding_tensor = self.model.encode_batch(audio_tensor)

        # Convert to numpy
        embedding_vector = embedding_tensor.squeeze().cpu().numpy()

        duration = len(audio) / sample_rate

        return VoiceEmbedding(
            embedding=embedding_vector,
            duration=duration,
            metadata={
                "model": self.model_source,
                "sample_rate": sample_rate
            }
        )

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
        # Convert to tensors
        emb1_tensor = torch.from_numpy(embedding1).unsqueeze(0)
        emb2_tensor = torch.from_numpy(embedding2).unsqueeze(0)

        # Use SpeechBrain's similarity function
        similarity = self.model.similarity(emb1_tensor, emb2_tensor)

        # Convert to float and normalize to [0, 1]
        score = float(similarity.item())
        score = (score + 1) / 2  # Convert from [-1, 1] to [0, 1]

        return score

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
