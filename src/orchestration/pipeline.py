"""
Complete transcription pipeline integrating all components

This follows the Facade Pattern to provide a simple interface
to the complex subsystems.
"""

import numpy as np
from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
import uuid
from datetime import datetime

from ..audio_capture.base import AudioCaptureInterface
from ..transcription.base import TranscriptionInterface, TranscriptionResult
from ..diarization.base import DiarizationInterface, DiarizationResult
from ..voice_recognition.base import VoiceRecognitionInterface, SpeakerProfile
from ..database import DatabaseInterface, SpeakerRepository, MeetingRepository, Meeting, Transcript

logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """
    Complete pipeline for meeting transcription with speaker identification

    This class orchestrates the entire workflow:
    1. Audio capture
    2. Speech-to-text transcription
    3. Speaker diarization
    4. Voice recognition and speaker identification
    5. Persistence to database
    """

    def __init__(
        self,
        transcriber: TranscriptionInterface,
        diarizer: Optional[DiarizationInterface] = None,
        voice_recognizer: Optional[VoiceRecognitionInterface] = None,
        database: Optional[DatabaseInterface] = None,
        enable_speaker_recognition: bool = True
    ):
        """
        Initialize transcription pipeline

        Args:
            transcriber: Speech-to-text transcriber
            diarizer: Speaker diarization system (optional)
            voice_recognizer: Voice recognition system (optional)
            database: Database for persistence (optional)
            enable_speaker_recognition: Enable speaker identification
        """
        self.transcriber = transcriber
        self.diarizer = diarizer
        self.voice_recognizer = voice_recognizer
        self.database = database
        self.enable_speaker_recognition = enable_speaker_recognition

        # Initialize repositories if database provided
        self.speaker_repo = None
        self.meeting_repo = None
        if database:
            self.speaker_repo = SpeakerRepository(database)
            self.meeting_repo = MeetingRepository(database)

        logger.info("TranscriptionPipeline initialized")

    def process_audio_file(
        self,
        audio_path: str,
        meeting_id: Optional[str] = None,
        language: Optional[str] = None,
        num_speakers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process audio file through complete pipeline

        Args:
            audio_path: Path to audio file
            meeting_id: Meeting ID (auto-generated if not provided)
            language: Language code (auto-detect if not provided)
            num_speakers: Number of speakers (auto-detect if not provided)

        Returns:
            Dict containing transcription, diarization, and speaker info
        """
        logger.info(f"Processing audio file: {audio_path}")

        if meeting_id is None:
            meeting_id = str(uuid.uuid4())

        # Step 1: Transcription
        logger.info("Step 1: Transcribing audio...")
        transcription = self.transcriber.transcribe_file(audio_path, language)

        # Step 2: Speaker diarization
        diarization = None
        if self.diarizer:
            logger.info("Step 2: Performing speaker diarization...")
            diarization = self.diarizer.diarize_file(
                audio_path,
                num_speakers=num_speakers
            )

        # Step 3: Combine transcription with diarization
        if diarization:
            logger.info("Step 3: Combining transcription with speaker labels...")
            self._assign_speakers_to_segments(transcription, diarization)

        # Step 4: Speaker recognition
        if self.enable_speaker_recognition and self.voice_recognizer and self.speaker_repo:
            logger.info("Step 4: Recognizing speakers...")
            self._recognize_speakers(audio_path, transcription, diarization)

        # Step 5: Save to database
        if self.meeting_repo:
            logger.info("Step 5: Saving to database...")
            self._save_to_database(meeting_id, transcription, audio_path)

        result = {
            "meeting_id": meeting_id,
            "transcription": transcription,
            "diarization": diarization,
            "duration": transcription.duration,
            "num_speakers": diarization.num_speakers if diarization else None
        }

        logger.info(f"Processing complete: {meeting_id}")
        return result

    def _assign_speakers_to_segments(
        self,
        transcription: TranscriptionResult,
        diarization: DiarizationResult
    ):
        """Assign speaker labels to transcription segments"""
        for segment in transcription.segments:
            # Find speaker at segment midpoint
            midpoint = (segment.start + segment.end) / 2
            speaker_id = diarization.get_speaker_at_time(midpoint)

            if speaker_id:
                segment.speaker = speaker_id

    def _recognize_speakers(
        self,
        audio_path: str,
        transcription: TranscriptionResult,
        diarization: Optional[DiarizationResult]
    ):
        """Recognize speakers against known profiles"""
        if not self.voice_recognizer or not self.speaker_repo:
            return

        # Load known speaker profiles
        known_speakers = self.speaker_repo.list_all()

        # Load audio file
        import soundfile as sf
        audio, sample_rate = sf.read(audio_path, dtype='float32')

        # Map diarization labels to real identities
        speaker_mapping = {}

        for segment in transcription.segments:
            if not segment.speaker or segment.speaker in speaker_mapping:
                continue

            # Extract audio for this segment
            start_sample = int(segment.start * sample_rate)
            end_sample = int(segment.end * sample_rate)
            segment_audio = audio[start_sample:end_sample]

            # Recognize speaker
            result = self.voice_recognizer.recognize_speaker(
                segment_audio,
                sample_rate,
                known_speakers,
                threshold=0.7
            )

            if result.speaker_id:
                speaker_mapping[segment.speaker] = result.speaker_id
                logger.info(
                    f"Recognized {segment.speaker} as {result.speaker_id} "
                    f"(confidence: {result.confidence:.2f})"
                )

        # Apply mapping to all segments
        for segment in transcription.segments:
            if segment.speaker in speaker_mapping:
                segment.speaker = speaker_mapping[segment.speaker]

    def _save_to_database(
        self,
        meeting_id: str,
        transcription: TranscriptionResult,
        audio_path: str
    ):
        """Save transcription to database"""
        if not self.meeting_repo:
            return

        # Create meeting record
        meeting = Meeting(
            meeting_id=meeting_id,
            title=f"Meeting {meeting_id[:8]}",
            platform="local",
            start_time=datetime.now(),
            duration=transcription.duration,
            metadata={"audio_file": audio_path}
        )

        self.meeting_repo.create(meeting)

        # Save transcript segments
        for segment in transcription.segments:
            transcript = Transcript(
                transcript_id=None,
                meeting_id=meeting_id,
                text=segment.text,
                start_time=segment.start,
                end_time=segment.end,
                speaker_id=segment.speaker,
                confidence=segment.confidence
            )
            self.meeting_repo.add_transcript(transcript)

    def register_speaker_from_audio(
        self,
        audio_path: str,
        speaker_id: str,
        name: str,
        email: Optional[str] = None
    ) -> SpeakerProfile:
        """
        Register a new speaker from audio sample

        Args:
            audio_path: Path to audio sample
            speaker_id: Unique speaker ID
            name: Speaker name
            email: Speaker email

        Returns:
            SpeakerProfile: Created speaker profile
        """
        if not self.voice_recognizer or not self.speaker_repo:
            raise RuntimeError("Voice recognition and database required")

        logger.info(f"Registering speaker: {name} ({speaker_id})")

        # Extract voice embedding
        embedding = self.voice_recognizer.extract_embedding_from_file(audio_path)

        # Create profile
        profile = SpeakerProfile(
            speaker_id=speaker_id,
            name=name,
            email=email,
            embeddings=[embedding]
        )

        # Save to database
        self.speaker_repo.create(profile)

        logger.info(f"Speaker registered: {speaker_id}")
        return profile

    def get_meeting_transcript(self, meeting_id: str) -> Optional[str]:
        """
        Get formatted transcript for a meeting

        Args:
            meeting_id: Meeting ID

        Returns:
            Optional[str]: Formatted transcript text
        """
        if not self.meeting_repo:
            return None

        return self.meeting_repo.get_full_transcript_text(meeting_id)
