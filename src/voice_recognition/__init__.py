"""
Voice recognition and speaker embedding module
"""

from .base import VoiceRecognitionInterface, SpeakerProfile, VoiceEmbedding
from .wespeaker_recognizer import WeSpeakerRecognizer
from .speechbrain_recognizer import SpeechBrainRecognizer

__all__ = [
    "VoiceRecognitionInterface",
    "SpeakerProfile",
    "VoiceEmbedding",
    "WeSpeakerRecognizer",
    "SpeechBrainRecognizer"
]
