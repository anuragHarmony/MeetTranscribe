"""Audio capture implementations."""

import asyncio
import logging
from datetime import datetime
from typing import AsyncIterator, Optional

import numpy as np
import sounddevice as sd

from src.core.config import AudioConfig
from src.core.interfaces import AudioChunk, AudioSource, IAudioCapture

logger = logging.getLogger(__name__)


class LocalAudioCapture(IAudioCapture):
    """Captures audio from local microphone."""

    def __init__(self, config: AudioConfig, device_index: Optional[int] = None):
        """
        Initialize local audio capture.

        Args:
            config: Audio configuration
            device_index: Specific device index to use
        """
        self.config = config
        self.device_index = device_index or config.device_index
        self._stream: Optional[sd.InputStream] = None
        self._is_active = False
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()

    async def start(self) -> None:
        """Start capturing audio from microphone."""
        if self._is_active:
            logger.warning("Audio capture already active")
            return

        logger.info(f"Starting audio capture from device {self.device_index}")

        def callback(indata, frames, time_info, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"Audio capture status: {status}")

            audio_data = indata.copy().flatten()
            chunk = AudioChunk(
                data=audio_data,
                sample_rate=self.config.sample_rate,
                timestamp=datetime.now(),
                source=AudioSource.LOCAL_MIC,
                duration_ms=len(audio_data) / self.config.sample_rate * 1000,
            )

            # Put in queue (non-blocking)
            try:
                self._audio_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                logger.warning("Audio queue full, dropping chunk")

        self._stream = sd.InputStream(
            device=self.device_index,
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            callback=callback,
            blocksize=int(self.config.sample_rate * self.config.chunk_duration_ms / 1000),
        )

        self._stream.start()
        self._is_active = True
        logger.info("Audio capture started")

    async def stop(self) -> None:
        """Stop capturing audio."""
        if not self._is_active:
            return

        logger.info("Stopping audio capture")
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_active = False
        logger.info("Audio capture stopped")

    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get stream of audio chunks."""
        while self._is_active or not self._audio_queue.empty():
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
                yield chunk
            except asyncio.TimeoutError:
                if not self._is_active:
                    break
                continue

    def is_active(self) -> bool:
        """Check if capture is active."""
        return self._is_active


class SystemAudioCapture(IAudioCapture):
    """Captures system audio output."""

    def __init__(self, config: AudioConfig):
        """
        Initialize system audio capture.

        Args:
            config: Audio configuration
        """
        self.config = config
        self._is_active = False
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
        self._stream: Optional[sd.InputStream] = None

    async def start(self) -> None:
        """Start capturing system audio."""
        if self._is_active:
            logger.warning("System audio capture already active")
            return

        logger.info("Starting system audio capture")

        # Find loopback/monitor device
        devices = sd.query_devices()
        loopback_device = None

        for idx, device in enumerate(devices):
            # Look for monitor/loopback device
            if "monitor" in device["name"].lower() or "loopback" in device["name"].lower():
                loopback_device = idx
                break

        if loopback_device is None:
            logger.warning("No loopback device found, using default input")
            loopback_device = sd.default.device[0]

        def callback(indata, frames, time_info, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"System audio capture status: {status}")

            audio_data = indata.copy().flatten()
            chunk = AudioChunk(
                data=audio_data,
                sample_rate=self.config.sample_rate,
                timestamp=datetime.now(),
                source=AudioSource.SYSTEM_AUDIO,
                duration_ms=len(audio_data) / self.config.sample_rate * 1000,
            )

            try:
                self._audio_queue.put_nowait(chunk)
            except asyncio.QueueFull:
                logger.warning("System audio queue full, dropping chunk")

        self._stream = sd.InputStream(
            device=loopback_device,
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            callback=callback,
            blocksize=int(self.config.sample_rate * self.config.chunk_duration_ms / 1000),
        )

        self._stream.start()
        self._is_active = True
        logger.info(f"System audio capture started on device {loopback_device}")

    async def stop(self) -> None:
        """Stop capturing system audio."""
        if not self._is_active:
            return

        logger.info("Stopping system audio capture")
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_active = False
        logger.info("System audio capture stopped")

    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get stream of audio chunks."""
        while self._is_active or not self._audio_queue.empty():
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
                yield chunk
            except asyncio.TimeoutError:
                if not self._is_active:
                    break
                continue

    def is_active(self) -> bool:
        """Check if capture is active."""
        return self._is_active


class CombinedAudioCapture(IAudioCapture):
    """Captures and combines both microphone and system audio."""

    def __init__(self, config: AudioConfig, device_index: Optional[int] = None):
        """
        Initialize combined audio capture.

        Args:
            config: Audio configuration
            device_index: Specific device index for microphone
        """
        self.config = config
        self.mic_capture = LocalAudioCapture(config, device_index)
        self.system_capture = SystemAudioCapture(config)
        self._is_active = False
        self._audio_queue: asyncio.Queue[AudioChunk] = asyncio.Queue()
        self._mix_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start capturing both audio sources."""
        if self._is_active:
            logger.warning("Combined audio capture already active")
            return

        logger.info("Starting combined audio capture")
        await self.mic_capture.start()
        await self.system_capture.start()
        self._is_active = True

        # Start mixing task
        self._mix_task = asyncio.create_task(self._mix_audio_streams())

    async def _mix_audio_streams(self) -> None:
        """Mix microphone and system audio streams."""
        mic_buffer = []
        sys_buffer = []
        buffer_duration_ms = self.config.chunk_duration_ms

        async def consume_stream(capture: IAudioCapture, buffer: list):
            """Consume audio stream into buffer."""
            async for chunk in capture.get_audio_stream():
                buffer.append(chunk)

        # Create tasks for both streams
        mic_task = asyncio.create_task(
            consume_stream(self.mic_capture, mic_buffer)
        )
        sys_task = asyncio.create_task(
            consume_stream(self.system_capture, sys_buffer)
        )

        while self._is_active:
            await asyncio.sleep(buffer_duration_ms / 1000)

            if mic_buffer or sys_buffer:
                # Mix available chunks
                mic_data = np.concatenate([c.data for c in mic_buffer]) if mic_buffer else np.zeros(0)
                sys_data = np.concatenate([c.data for c in sys_buffer]) if sys_buffer else np.zeros(0)

                # Ensure same length
                max_len = max(len(mic_data), len(sys_data))
                if max_len > 0:
                    if len(mic_data) < max_len:
                        mic_data = np.pad(mic_data, (0, max_len - len(mic_data)))
                    if len(sys_data) < max_len:
                        sys_data = np.pad(sys_data, (0, max_len - len(sys_data)))

                    # Mix: 50% mic, 50% system audio
                    mixed_data = (mic_data * 0.5 + sys_data * 0.5).astype(np.float32)

                    chunk = AudioChunk(
                        data=mixed_data,
                        sample_rate=self.config.sample_rate,
                        timestamp=datetime.now(),
                        source=AudioSource.COMBINED,
                        duration_ms=len(mixed_data) / self.config.sample_rate * 1000,
                    )

                    try:
                        await self._audio_queue.put(chunk)
                    except asyncio.QueueFull:
                        logger.warning("Combined audio queue full, dropping chunk")

                # Clear buffers
                mic_buffer.clear()
                sys_buffer.clear()

        # Cancel tasks
        mic_task.cancel()
        sys_task.cancel()

    async def stop(self) -> None:
        """Stop capturing both audio sources."""
        if not self._is_active:
            return

        logger.info("Stopping combined audio capture")
        self._is_active = False

        if self._mix_task:
            self._mix_task.cancel()
            try:
                await self._mix_task
            except asyncio.CancelledError:
                pass

        await self.mic_capture.stop()
        await self.system_capture.stop()
        logger.info("Combined audio capture stopped")

    async def get_audio_stream(self) -> AsyncIterator[AudioChunk]:
        """Get stream of mixed audio chunks."""
        while self._is_active or not self._audio_queue.empty():
            try:
                chunk = await asyncio.wait_for(self._audio_queue.get(), timeout=1.0)
                yield chunk
            except asyncio.TimeoutError:
                if not self._is_active:
                    break
                continue

    def is_active(self) -> bool:
        """Check if capture is active."""
        return self._is_active
