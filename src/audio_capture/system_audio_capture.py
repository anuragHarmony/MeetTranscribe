"""
System audio capture implementation (captures what computer is playing)
"""

import sounddevice as sd
import numpy as np
from typing import Generator, Tuple, Optional
import queue
from .base import AudioCaptureInterface


class SystemAudioCapture(AudioCaptureInterface):
    """
    Captures system audio output (loopback recording)

    Note: On Linux, this requires PulseAudio or PipeWire with proper configuration
    On Windows, this requires WASAPI loopback mode
    On macOS, this may require BlackHole or similar virtual audio device
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 0.5,
        device: Optional[int] = None
    ):
        """
        Initialize system audio capture

        Args:
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            chunk_duration: Duration of each audio chunk in seconds
            device: Loopback device ID (None for default)
        """
        self._sample_rate = sample_rate
        self._channels = channels
        self._chunk_duration = chunk_duration
        self._device = device
        self._chunk_size = int(sample_rate * chunk_duration)

        self._recording = False
        self._stream = None
        self._audio_queue = queue.Queue()

    def start(self) -> None:
        """Start system audio recording"""
        if self._recording:
            return

        self._recording = True
        self._audio_queue = queue.Queue()

        def audio_callback(indata, frames, time, status):
            if status:
                print(f"System audio callback status: {status}")
            if self._recording:
                self._audio_queue.put(indata.copy())

        # For system audio, we need to use loopback mode
        # This is platform-specific and may require special configuration
        self._stream = sd.InputStream(
            device=self._device,
            channels=self._channels,
            samplerate=self._sample_rate,
            blocksize=self._chunk_size,
            callback=audio_callback,
            dtype=np.float32
        )

        self._stream.start()

    def stop(self) -> None:
        """Stop system audio recording"""
        if not self._recording:
            return

        self._recording = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_audio_stream(self) -> Generator[Tuple[np.ndarray, int], None, None]:
        """
        Get audio stream from system audio

        Yields:
            Tuple[np.ndarray, int]: (audio_data, sample_rate)
        """
        while self._recording or not self._audio_queue.empty():
            try:
                audio_data = self._audio_queue.get(timeout=1.0)
                # Convert to mono if stereo
                if audio_data.ndim > 1:
                    audio_data = audio_data.mean(axis=1)
                yield audio_data, self._sample_rate
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

    @staticmethod
    def find_loopback_device():
        """
        Try to find the loopback/monitor device for system audio

        Returns:
            Optional[int]: Device ID or None if not found
        """
        devices = sd.query_devices()

        # Look for loopback/monitor devices
        loopback_keywords = ['loopback', 'monitor', 'stereo mix', 'wave out', 'wasapi']

        for idx, device in enumerate(devices):
            device_name = device['name'].lower()
            if any(keyword in device_name for keyword in loopback_keywords):
                if device['max_input_channels'] > 0:
                    return idx

        return None
