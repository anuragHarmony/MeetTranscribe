"""
Dual audio capture: simultaneously captures microphone and system audio
"""

import numpy as np
from typing import Generator, Tuple, Optional
import threading
import queue
from .base import AudioCaptureInterface
from .microphone_capture import MicrophoneCapture
from .system_audio_capture import SystemAudioCapture


class DualAudioCapture(AudioCaptureInterface):
    """
    Captures both microphone and system audio simultaneously and mixes them

    This is useful for capturing complete meeting audio:
    - Microphone: User's voice
    - System audio: Other participants' voices
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 0.5,
        mic_device: Optional[int] = None,
        system_device: Optional[int] = None,
        mix_ratio: Tuple[float, float] = (1.0, 1.0)
    ):
        """
        Initialize dual audio capture

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            chunk_duration: Duration of each audio chunk in seconds
            mic_device: Microphone device ID
            system_device: System audio device ID
            mix_ratio: (mic_weight, system_weight) for mixing
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_duration = chunk_duration
        self._mix_ratio = mix_ratio

        # Create separate capture instances
        self._mic_capture = MicrophoneCapture(
            sample_rate=sample_rate,
            channels=channels,
            chunk_duration=chunk_duration,
            device=mic_device
        )

        self._system_capture = SystemAudioCapture(
            sample_rate=sample_rate,
            channels=channels,
            chunk_duration=chunk_duration,
            device=system_device
        )

        self._recording = False
        self._mixed_queue = queue.Queue()
        self._mixer_thread = None

    def start(self) -> None:
        """Start dual audio recording"""
        if self._recording:
            return

        self._recording = True
        self._mixed_queue = queue.Queue()

        # Start both captures
        self._mic_capture.start()
        self._system_capture.start()

        # Start mixer thread
        self._mixer_thread = threading.Thread(target=self._mix_audio_streams)
        self._mixer_thread.daemon = True
        self._mixer_thread.start()

    def stop(self) -> None:
        """Stop dual audio recording"""
        if not self._recording:
            return

        self._recording = False

        # Stop both captures
        self._mic_capture.stop()
        self._system_capture.stop()

        # Wait for mixer thread
        if self._mixer_thread:
            self._mixer_thread.join(timeout=2.0)
            self._mixer_thread = None

    def _mix_audio_streams(self) -> None:
        """Mix audio from both sources in separate thread"""
        mic_stream = self._mic_capture.get_audio_stream()
        system_stream = self._system_capture.get_audio_stream()

        mic_weight, system_weight = self._mix_ratio

        try:
            while self._recording:
                try:
                    # Get audio from both sources
                    mic_data, mic_sr = next(mic_stream)
                    system_data, system_sr = next(system_stream)

                    # Ensure same length (pad if necessary)
                    max_len = max(len(mic_data), len(system_data))
                    if len(mic_data) < max_len:
                        mic_data = np.pad(mic_data, (0, max_len - len(mic_data)))
                    if len(system_data) < max_len:
                        system_data = np.pad(system_data, (0, max_len - len(system_data)))

                    # Mix audio
                    mixed_data = (mic_weight * mic_data + system_weight * system_data) / 2.0

                    # Normalize to prevent clipping
                    max_val = np.max(np.abs(mixed_data))
                    if max_val > 1.0:
                        mixed_data = mixed_data / max_val

                    self._mixed_queue.put((mixed_data, self._sample_rate))

                except StopIteration:
                    break
                except Exception as e:
                    print(f"Error in audio mixing: {e}")
                    break

        except Exception as e:
            print(f"Mixer thread error: {e}")

    def get_audio_stream(self) -> Generator[Tuple[np.ndarray, int], None, None]:
        """
        Get mixed audio stream

        Yields:
            Tuple[np.ndarray, int]: (mixed_audio_data, sample_rate)
        """
        while self._recording or not self._mixed_queue.empty():
            try:
                audio_data, sample_rate = self._mixed_queue.get(timeout=1.0)
                yield audio_data, sample_rate
            except queue.Empty:
                if not self._recording:
                    break
                continue

    def is_recording(self) -> bool:
        """Check if currently recording"""
        return self._recording

    @property
    def sample_rate(self) -> int:
        """Get sample rate"""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Get number of channels"""
        return self._channels

    def get_separate_streams(self) -> Tuple[Generator, Generator]:
        """
        Get separate streams for microphone and system audio
        Useful for separate processing

        Returns:
            Tuple[Generator, Generator]: (mic_stream, system_stream)
        """
        return (
            self._mic_capture.get_audio_stream(),
            self._system_capture.get_audio_stream()
        )
