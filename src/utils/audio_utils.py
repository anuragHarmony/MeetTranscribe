"""
Audio processing utilities
"""

import numpy as np
from typing import Tuple
import soundfile as sf


def resample_audio(
    audio: np.ndarray,
    orig_sr: int,
    target_sr: int
) -> np.ndarray:
    """
    Resample audio to target sample rate

    Args:
        audio: Audio data
        orig_sr: Original sample rate
        target_sr: Target sample rate

    Returns:
        Resampled audio
    """
    if orig_sr == target_sr:
        return audio

    try:
        import librosa
        return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr)
    except ImportError:
        # Fallback to scipy
        from scipy import signal
        num_samples = int(len(audio) * target_sr / orig_sr)
        return signal.resample(audio, num_samples)


def normalize_audio(audio: np.ndarray, target_level: float = -20.0) -> np.ndarray:
    """
    Normalize audio to target level in dB

    Args:
        audio: Audio data
        target_level: Target level in dB

    Returns:
        Normalized audio
    """
    # Calculate RMS
    rms = np.sqrt(np.mean(audio ** 2))

    if rms == 0:
        return audio

    # Convert to dB
    current_db = 20 * np.log10(rms)

    # Calculate gain
    gain_db = target_level - current_db
    gain = 10 ** (gain_db / 20)

    # Apply gain
    normalized = audio * gain

    # Prevent clipping
    max_val = np.max(np.abs(normalized))
    if max_val > 1.0:
        normalized = normalized / max_val

    return normalized


def detect_silence(
    audio: np.ndarray,
    sample_rate: int,
    threshold_db: float = -40.0,
    min_silence_duration: float = 0.5
) -> list:
    """
    Detect silence segments in audio

    Args:
        audio: Audio data
        sample_rate: Sample rate
        threshold_db: Silence threshold in dB
        min_silence_duration: Minimum silence duration in seconds

    Returns:
        List of (start, end) tuples for silence segments
    """
    # Convert to dB
    audio_abs = np.abs(audio)
    audio_abs[audio_abs == 0] = 1e-10  # Avoid log(0)
    audio_db = 20 * np.log10(audio_abs)

    # Find silence
    is_silence = audio_db < threshold_db

    # Find continuous silence segments
    silence_segments = []
    in_silence = False
    silence_start = 0

    min_samples = int(min_silence_duration * sample_rate)

    for i, silent in enumerate(is_silence):
        if silent and not in_silence:
            silence_start = i
            in_silence = True
        elif not silent and in_silence:
            silence_end = i
            if silence_end - silence_start >= min_samples:
                silence_segments.append((
                    silence_start / sample_rate,
                    silence_end / sample_rate
                ))
            in_silence = False

    # Handle if ending in silence
    if in_silence and len(audio) - silence_start >= min_samples:
        silence_segments.append((
            silence_start / sample_rate,
            len(audio) / sample_rate
        ))

    return silence_segments


def save_audio(
    audio: np.ndarray,
    sample_rate: int,
    filepath: str,
    format: str = "WAV"
) -> str:
    """
    Save audio to file

    Args:
        audio: Audio data
        sample_rate: Sample rate
        filepath: Output file path
        format: Audio format (WAV, FLAC, OGG, etc.)

    Returns:
        Path to saved file
    """
    sf.write(filepath, audio, sample_rate, format=format)
    return filepath


def load_audio(filepath: str, target_sr: int = None) -> Tuple[np.ndarray, int]:
    """
    Load audio from file

    Args:
        filepath: Path to audio file
        target_sr: Target sample rate (None to keep original)

    Returns:
        Tuple of (audio_data, sample_rate)
    """
    audio, sr = sf.read(filepath, dtype='float32')

    # Convert to mono if stereo
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Resample if needed
    if target_sr and sr != target_sr:
        audio = resample_audio(audio, sr, target_sr)
        sr = target_sr

    return audio, sr
