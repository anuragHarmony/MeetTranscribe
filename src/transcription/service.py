"""Main transcription service that orchestrates all components."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional

import numpy as np

from src.audio.capture import CombinedAudioCapture, LocalAudioCapture
from src.core.config import Config, get_config
from src.core.interfaces import (
    AudioChunk,
    AudioSource,
    MeetingMetadata,
    MeetingPlatform,
    TranscriptionSegment,
    VoiceProfile,
)
from src.platforms.google_meet import GoogleMeetIntegration
from src.platforms.slack import SlackIntegration
from src.platforms.teams import TeamsIntegration
from src.platforms.zoom import ZoomIntegration
from src.speaker.diarization import PyAnnoteDiarization
from src.speaker.identification import SpeechBrainIdentification
from src.storage.voice_profiles import VoiceProfileStorage
from src.transcription.whisper_engine import WhisperTranscriptionEngine

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Main service for meeting transcription."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize transcription service.

        Args:
            config: Configuration (uses global config if None)
        """
        self.config = config or get_config()

        # Initialize components
        self.audio_capture = None
        self.platform_integration = None
        self.transcription_engine = WhisperTranscriptionEngine(self.config.whisper)
        self.diarization_engine = PyAnnoteDiarization(self.config.diarization)
        self.storage = VoiceProfileStorage(self.config.storage)
        self.speaker_identification = SpeechBrainIdentification(
            self.config.speaker_recognition, self.storage
        )

        self._is_initialized = False
        self._is_recording = False
        self._mode: Optional[str] = None
        self._platform: Optional[MeetingPlatform] = None

    async def initialize(self) -> None:
        """Initialize all components."""
        if self._is_initialized:
            logger.warning("Service already initialized")
            return

        logger.info("Initializing transcription service")

        # Initialize storage first
        await self.storage.initialize()

        # Initialize ML models
        await self.transcription_engine.initialize()
        await self.diarization_engine.initialize()
        await self.speaker_identification.initialize()

        self._is_initialized = True
        logger.info("Transcription service initialized")

    async def start_local_recording(
        self, capture_mode: str = "combined"
    ) -> AsyncIterator[Dict]:
        """
        Start local recording mode.

        Args:
            capture_mode: "mic", "system", or "combined"

        Yields:
            Transcription results with speaker info
        """
        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Starting local recording (mode: {capture_mode})")

        # Setup audio capture
        if capture_mode == "mic":
            self.audio_capture = LocalAudioCapture(self.config.audio)
        elif capture_mode == "combined":
            self.audio_capture = CombinedAudioCapture(self.config.audio)
        else:
            raise ValueError(f"Invalid capture mode: {capture_mode}")

        self._mode = "local"
        self._is_recording = True

        # Start capture
        await self.audio_capture.start()

        # Process audio stream
        async for result in self._process_audio_stream(
            self.audio_capture.get_audio_stream()
        ):
            yield result

    async def start_online_meeting(
        self,
        platform: str,
        meeting_url: str,
        credentials: Optional[Dict[str, str]] = None,
    ) -> AsyncIterator[Dict]:
        """
        Start online meeting mode.

        Args:
            platform: Platform name ("google_meet", "zoom", "teams", "slack")
            meeting_url: Meeting URL
            credentials: Optional login credentials

        Yields:
            Transcription results with speaker info
        """
        if not self._is_initialized:
            await self.initialize()

        logger.info(f"Starting online meeting on {platform}")

        # Create platform integration
        if platform == "google_meet":
            self.platform_integration = GoogleMeetIntegration(self.config.platform)
            self._platform = MeetingPlatform.GOOGLE_MEET
        elif platform == "zoom":
            self.platform_integration = ZoomIntegration(self.config.platform)
            self._platform = MeetingPlatform.ZOOM
        elif platform == "teams":
            self.platform_integration = TeamsIntegration(self.config.platform)
            self._platform = MeetingPlatform.MICROSOFT_TEAMS
        elif platform == "slack":
            self.platform_integration = SlackIntegration(self.config.platform)
            self._platform = MeetingPlatform.SLACK_HUDDLE
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        self._mode = "online"
        self._is_recording = True

        # Connect to meeting
        await self.platform_integration.connect(meeting_url, credentials)

        # Get meeting metadata
        try:
            metadata = await self.platform_integration.get_metadata()
            logger.info(f"Meeting metadata: {metadata.meeting_id}")

            # Create voice profiles for participants if metadata available
            await self._process_meeting_participants(metadata)
        except Exception as e:
            logger.warning(f"Could not get meeting metadata: {e}")

        # Process audio stream
        async for result in self._process_audio_stream(
            self.platform_integration.get_audio_stream()
        ):
            yield result

    async def _process_audio_stream(
        self, audio_stream: AsyncIterator[AudioChunk]
    ) -> AsyncIterator[Dict]:
        """
        Process audio stream and yield transcription results.

        Args:
            audio_stream: Stream of audio chunks

        Yields:
            Transcription results
        """
        buffer = []
        buffer_duration_ms = 0
        process_interval_ms = 10000  # Process every 10 seconds

        async for chunk in audio_stream:
            if not self._is_recording:
                break

            buffer.append(chunk)
            buffer_duration_ms += chunk.duration_ms

            # Process when buffer is large enough
            if buffer_duration_ms >= process_interval_ms:
                # Concatenate audio
                audio_data = np.concatenate([c.data for c in buffer])
                sample_rate = buffer[0].sample_rate

                combined_chunk = AudioChunk(
                    data=audio_data,
                    sample_rate=sample_rate,
                    timestamp=buffer[0].timestamp,
                    source=buffer[0].source,
                    duration_ms=buffer_duration_ms,
                )

                # Process chunk
                result = await self._process_chunk(combined_chunk)
                if result:
                    yield result

                # Clear buffer
                buffer.clear()
                buffer_duration_ms = 0

        # Process remaining buffer
        if buffer:
            audio_data = np.concatenate([c.data for c in buffer])
            sample_rate = buffer[0].sample_rate

            combined_chunk = AudioChunk(
                data=audio_data,
                sample_rate=sample_rate,
                timestamp=buffer[0].timestamp,
                source=buffer[0].source,
                duration_ms=buffer_duration_ms,
            )

            result = await self._process_chunk(combined_chunk)
            if result:
                yield result

    async def _process_chunk(self, audio: AudioChunk) -> Optional[Dict]:
        """
        Process single audio chunk.

        Args:
            audio: Audio chunk

        Returns:
            Processing result
        """
        try:
            # Transcribe
            transcription_segments = await self.transcription_engine.transcribe(audio)

            if not transcription_segments:
                return None

            # Diarize
            speaker_segments = await self.diarization_engine.diarize(audio)

            # Match transcription with speakers
            matched_segments = self._match_transcription_with_speakers(
                transcription_segments, speaker_segments
            )

            # Identify speakers
            for segment in matched_segments:
                if segment.get("speaker_id"):
                    # Extract speaker audio segment
                    start_sample = int(segment["start_time"] * audio.sample_rate)
                    end_sample = int(segment["end_time"] * audio.sample_rate)
                    speaker_audio = audio.data[start_sample:end_sample]

                    if len(speaker_audio) > audio.sample_rate:  # At least 1 second
                        speaker_chunk = AudioChunk(
                            data=speaker_audio,
                            sample_rate=audio.sample_rate,
                            timestamp=audio.timestamp,
                            source=audio.source,
                            duration_ms=(end_sample - start_sample)
                            / audio.sample_rate
                            * 1000,
                        )

                        # Extract embedding and identify
                        embedding = await self.speaker_identification.extract_embedding(
                            speaker_chunk
                        )
                        profile = await self.speaker_identification.identify_speaker(
                            embedding
                        )

                        if profile:
                            segment["speaker_name"] = profile.name
                            segment["speaker_email"] = profile.email

                            # Update profile with new sample
                            updated_embedding = await self.speaker_identification.update_profile_with_new_sample(
                                profile, embedding
                            )
                            await self.storage.update_profile_embedding(
                                profile.profile_id, updated_embedding
                            )

            return {
                "timestamp": audio.timestamp.isoformat(),
                "duration_ms": audio.duration_ms,
                "segments": matched_segments,
                "source": audio.source.value,
            }

        except Exception as e:
            logger.error(f"Error processing chunk: {e}", exc_info=True)
            return None

    def _match_transcription_with_speakers(
        self,
        transcription_segments: List[TranscriptionSegment],
        speaker_segments: List,
    ) -> List[Dict]:
        """
        Match transcription segments with speaker segments.

        Args:
            transcription_segments: Transcription segments
            speaker_segments: Speaker diarization segments

        Returns:
            Matched segments
        """
        matched = []

        for trans_seg in transcription_segments:
            # Find overlapping speaker segment
            speaker_id = None
            max_overlap = 0

            for speaker_seg in speaker_segments:
                # Calculate overlap
                overlap_start = max(trans_seg.start_time, speaker_seg.start_time)
                overlap_end = min(trans_seg.end_time, speaker_seg.end_time)
                overlap = max(0, overlap_end - overlap_start)

                if overlap > max_overlap:
                    max_overlap = overlap
                    speaker_id = speaker_seg.speaker_id

            matched.append(
                {
                    "text": trans_seg.text,
                    "start_time": trans_seg.start_time,
                    "end_time": trans_seg.end_time,
                    "confidence": trans_seg.confidence,
                    "speaker_id": speaker_id,
                    "speaker_name": None,
                    "speaker_email": None,
                }
            )

        return matched

    async def _process_meeting_participants(self, metadata: MeetingMetadata) -> None:
        """
        Process meeting participants and create/update profiles.

        Args:
            metadata: Meeting metadata
        """
        logger.info(f"Processing {len(metadata.participants)} participants")

        for participant in metadata.participants:
            email = participant.get("email")
            name = participant.get("name")

            if email:
                # Check if profile exists
                profile = await self.storage.get_profile_by_email(email)

                if profile is None:
                    # Create placeholder profile (will be updated with actual voice)
                    logger.info(f"Creating profile for {name} ({email})")
                    # Profile will be created when we first identify their voice

    async def stop(self) -> None:
        """Stop recording/transcription."""
        logger.info("Stopping transcription service")
        self._is_recording = False

        if self.audio_capture:
            await self.audio_capture.stop()

        if self.platform_integration:
            await self.platform_integration.disconnect()

        logger.info("Transcription service stopped")

    async def create_voice_profile(
        self, name: str, email: str, audio_samples: List[AudioChunk]
    ) -> VoiceProfile:
        """
        Create voice profile from audio samples.

        Args:
            name: Person's name
            email: Person's email
            audio_samples: List of audio samples (at least 3)

        Returns:
            Created voice profile
        """
        if not self._is_initialized:
            await self.initialize()

        if len(audio_samples) < self.config.speaker_recognition.min_samples_for_profile:
            raise ValueError(
                f"Need at least {self.config.speaker_recognition.min_samples_for_profile} samples"
            )

        logger.info(f"Creating voice profile for {name}")

        # Extract embeddings from all samples
        embeddings = []
        for sample in audio_samples:
            embedding = await self.speaker_identification.extract_embedding(sample)
            embeddings.append(embedding)

        # Average embeddings
        avg_embedding = np.mean(embeddings, axis=0)
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)

        # Create profile
        profile = VoiceProfile(
            profile_id=str(uuid.uuid4()),
            name=name,
            email=email,
            embedding=avg_embedding,
            sample_count=len(audio_samples),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Save profile
        await self.storage.save_profile(profile)

        logger.info(f"Voice profile created: {profile.profile_id}")
        return profile
