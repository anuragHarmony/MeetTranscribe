"""
Audio capture module for recording audio from various sources
"""

from .base import AudioCaptureInterface
from .microphone_capture import MicrophoneCapture
from .system_audio_capture import SystemAudioCapture
from .dual_capture import DualAudioCapture

__all__ = [
    "AudioCaptureInterface",
    "MicrophoneCapture",
    "SystemAudioCapture",
    "DualAudioCapture"
]
