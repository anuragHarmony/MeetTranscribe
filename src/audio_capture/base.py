"""
Base interface for audio capture following SOLID principles
"""

from abc import ABC, abstractmethod
from typing import Generator, Optional, Tuple
import numpy as np


class AudioCaptureInterface(ABC):
    """
    Interface for audio capture devices (Interface Segregation Principle)
    """

    @abstractmethod
    def start(self) -> None:
        """Start audio capture"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture"""
        pass

    @abstractmethod
    def get_audio_stream(self) -> Generator[Tuple[np.ndarray, int], None, None]:
        """
        Get audio stream as a generator

        Yields:
            Tuple[np.ndarray, int]: (audio_data, sample_rate)
        """
        pass

    @abstractmethod
    def is_recording(self) -> bool:
        """Check if currently recording"""
        pass

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Get sample rate"""
        pass

    @property
    @abstractmethod
    def channels(self) -> int:
        """Get number of channels"""
        pass


class AudioStorageInterface(ABC):
    """
    Interface for storing captured audio (Single Responsibility Principle)
    """

    @abstractmethod
    def save_audio(self, audio_data: np.ndarray, sample_rate: int, filename: str) -> str:
        """
        Save audio data to file

        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate in Hz
            filename: Name for the audio file

        Returns:
            str: Path to saved file
        """
        pass

    @abstractmethod
    def load_audio(self, filepath: str) -> Tuple[np.ndarray, int]:
        """
        Load audio data from file

        Args:
            filepath: Path to audio file

        Returns:
            Tuple[np.ndarray, int]: (audio_data, sample_rate)
        """
        pass
