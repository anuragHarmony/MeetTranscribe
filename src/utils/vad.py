"""
Voice Activity Detection (VAD) using Silero VAD

Silero VAD is state-of-the-art for VAD with:
- 95%+ accuracy
- 1ms latency per 32ms chunk
- 1.8MB model size
- MIT license
"""

import numpy as np
from typing import List, Tuple
import torch

try:
    import torchaudio
    from torchaudio.models import wav2vec2_model
except ImportError:
    torchaudio = None


class SileroVAD:
    """
    Silero Voice Activity Detector

    Detects speech vs silence/noise in audio for better transcription
    """

    def __init__(self, threshold: float = 0.5, sampling_rate: int = 16000):
        """
        Initialize Silero VAD

        Args:
            threshold: Detection threshold (0.0-1.0, higher = more conservative)
            sampling_rate: Audio sampling rate (8000 or 16000)
        """
        if torchaudio is None:
            raise ImportError(
                "torchaudio is not installed. "
                "Install it with: pip install torchaudio"
            )

        self.threshold = threshold
        self.sampling_rate = sampling_rate

        # Load Silero VAD model
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )

        # Extract utility functions
        (self.get_speech_timestamps,
         self.save_audio,
         self.read_audio,
         self.VADIterator,
         self.collect_chunks) = utils

    def detect_speech(
        self,
        audio: np.ndarray,
        return_timestamps: bool = True
    ) -> List[Tuple[float, float]]:
        """
        Detect speech segments in audio

        Args:
            audio: Audio data as numpy array (float32, mono)
            return_timestamps: Return timestamps or binary mask

        Returns:
            List of (start, end) tuples in seconds for speech segments
        """
        # Convert to torch tensor
        if isinstance(audio, np.ndarray):
            audio_tensor = torch.from_numpy(audio)
        else:
            audio_tensor = audio

        # Ensure correct sample rate
        if self.sampling_rate not in [8000, 16000]:
            raise ValueError("Silero VAD only supports 8kHz and 16kHz")

        # Get speech timestamps
        speech_timestamps = self.get_speech_timestamps(
            audio_tensor,
            self.model,
            sampling_rate=self.sampling_rate,
            threshold=self.threshold,
            min_speech_duration_ms=250,  # Minimum speech duration
            min_silence_duration_ms=100,  # Minimum silence between speeches
            speech_pad_ms=30  # Padding around speech
        )

        # Convert to seconds
        segments = [
            (ts['start'] / self.sampling_rate, ts['end'] / self.sampling_rate)
            for ts in speech_timestamps
        ]

        return segments

    def filter_audio(
        self,
        audio: np.ndarray,
        padding_ms: int = 100
    ) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
        """
        Filter audio to keep only speech segments

        Args:
            audio: Audio data as numpy array
            padding_ms: Padding around speech segments in milliseconds

        Returns:
            Tuple of (filtered_audio, speech_segments)
        """
        # Detect speech
        speech_segments = self.detect_speech(audio)

        if not speech_segments:
            # No speech detected
            return np.array([], dtype=audio.dtype), []

        # Extract speech segments with padding
        padding_samples = int(padding_ms * self.sampling_rate / 1000)
        filtered_chunks = []

        for start, end in speech_segments:
            start_sample = max(0, int(start * self.sampling_rate) - padding_samples)
            end_sample = min(len(audio), int(end * self.sampling_rate) + padding_samples)
            filtered_chunks.append(audio[start_sample:end_sample])

        # Concatenate all speech segments
        filtered_audio = np.concatenate(filtered_chunks)

        return filtered_audio, speech_segments

    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Check if audio chunk contains speech (for real-time)

        Args:
            audio_chunk: Audio chunk as numpy array

        Returns:
            bool: True if speech detected
        """
        if isinstance(audio_chunk, np.ndarray):
            audio_tensor = torch.from_numpy(audio_chunk)
        else:
            audio_tensor = audio_chunk

        # Get speech probability
        speech_prob = self.model(audio_tensor, self.sampling_rate).item()

        return speech_prob > self.threshold


def apply_vad_to_audio(
    audio: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.5
) -> Tuple[np.ndarray, List[Tuple[float, float]]]:
    """
    Convenience function to apply VAD to audio

    Args:
        audio: Audio data
        sample_rate: Sample rate
        threshold: Detection threshold

    Returns:
        Tuple of (filtered_audio, speech_segments)
    """
    vad = SileroVAD(threshold=threshold, sampling_rate=sample_rate)
    return vad.filter_audio(audio)
