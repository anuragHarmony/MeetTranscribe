"""
Real-time audio processing and transcription

Handles live audio streams from meetings or local capture
"""

import numpy as np
from typing import Optional, Callable, List
import logging
import threading
import queue
import time
from datetime import datetime
import uuid

from ..audio_capture.base import AudioCaptureInterface
from ..transcription.base import TranscriptionInterface
from ..diarization.base import DiarizationInterface
from ..voice_recognition.base import VoiceRecognitionInterface, SpeakerProfile
from ..database import DatabaseInterface, SpeakerRepository, MeetingRepository, Meeting, Transcript

logger = logging.getLogger(__name__)


class RealtimeProcessor:
    """
    Real-time audio processing and transcription

    Processes audio stream in chunks and provides near-realtime transcription
    """

    def __init__(
        self,
        audio_capture: AudioCaptureInterface,
        transcriber: TranscriptionInterface,
        diarizer: Optional[DiarizationInterface] = None,
        voice_recognizer: Optional[VoiceRecognitionInterface] = None,
        database: Optional[DatabaseInterface] = None,
        chunk_duration: float = 10.0,
        overlap: float = 2.0
    ):
        """
        Initialize real-time processor

        Args:
            audio_capture: Audio capture interface
            transcriber: Speech-to-text transcriber
            diarizer: Speaker diarization (optional)
            voice_recognizer: Voice recognition (optional)
            database: Database for persistence (optional)
            chunk_duration: Duration of audio chunks to process (seconds)
            overlap: Overlap between chunks for continuity (seconds)
        """
        self.audio_capture = audio_capture
        self.transcriber = transcriber
        self.diarizer = diarizer
        self.voice_recognizer = voice_recognizer
        self.database = database

        self.chunk_duration = chunk_duration
        self.overlap = overlap

        self.processing = False
        self.processor_thread = None
        self.audio_buffer = []
        self.sample_rate = audio_capture.sample_rate

        # Callbacks
        self.transcript_callback: Optional[Callable] = None
        self.speaker_callback: Optional[Callable] = None

        # Meeting metadata
        self.meeting_id = None
        self.meeting_start_time = None
        self.accumulated_audio_time = 0.0

        # Repositories
        self.speaker_repo = None
        self.meeting_repo = None
        if database:
            self.speaker_repo = SpeakerRepository(database)
            self.meeting_repo = MeetingRepository(database)

        # Known speakers cache
        self.known_speakers: List[SpeakerProfile] = []
        if self.speaker_repo:
            self.known_speakers = self.speaker_repo.list_all()

        logger.info("RealtimeProcessor initialized")

    def start(
        self,
        meeting_id: Optional[str] = None,
        meeting_title: str = "Live Meeting"
    ):
        """
        Start real-time processing

        Args:
            meeting_id: Meeting ID (auto-generated if not provided)
            meeting_title: Meeting title
        """
        if self.processing:
            logger.warning("Already processing")
            return

        logger.info("Starting real-time processing...")

        self.meeting_id = meeting_id or str(uuid.uuid4())
        self.meeting_start_time = datetime.now()
        self.accumulated_audio_time = 0.0
        self.audio_buffer = []

        # Create meeting record
        if self.meeting_repo:
            meeting = Meeting(
                meeting_id=self.meeting_id,
                title=meeting_title,
                platform="realtime",
                start_time=self.meeting_start_time
            )
            self.meeting_repo.create(meeting)

        # Start audio capture
        self.audio_capture.start()

        # Start processing thread
        self.processing = True
        self.processor_thread = threading.Thread(target=self._process_loop)
        self.processor_thread.daemon = True
        self.processor_thread.start()

        logger.info(f"Real-time processing started: {self.meeting_id}")

    def stop(self):
        """Stop real-time processing"""
        if not self.processing:
            return

        logger.info("Stopping real-time processing...")

        self.processing = False

        # Stop audio capture
        self.audio_capture.stop()

        # Wait for processor thread
        if self.processor_thread:
            self.processor_thread.join(timeout=5.0)

        # Process any remaining audio
        if len(self.audio_buffer) > 0:
            self._process_chunk(np.concatenate(self.audio_buffer))

        # Update meeting record
        if self.meeting_repo and self.meeting_id:
            meeting = self.meeting_repo.get(self.meeting_id)
            if meeting:
                meeting.end_time = datetime.now()
                meeting.duration = self.accumulated_audio_time
                self.meeting_repo.update(meeting)

        logger.info("Real-time processing stopped")

    def _process_loop(self):
        """Main processing loop"""
        chunk_samples = int(self.chunk_duration * self.sample_rate)
        overlap_samples = int(self.overlap * self.sample_rate)

        for audio_chunk, sr in self.audio_capture.get_audio_stream():
            if not self.processing:
                break

            # Add to buffer
            self.audio_buffer.append(audio_chunk)

            # Calculate total samples in buffer
            total_samples = sum(len(chunk) for chunk in self.audio_buffer)

            # Process if we have enough audio
            if total_samples >= chunk_samples:
                # Concatenate buffer
                audio_data = np.concatenate(self.audio_buffer)

                # Take chunk for processing
                process_chunk = audio_data[:chunk_samples]

                # Keep overlap for next iteration
                self.audio_buffer = [audio_data[chunk_samples - overlap_samples:]]

                # Process chunk in background
                threading.Thread(
                    target=self._process_chunk,
                    args=(process_chunk,),
                    daemon=True
                ).start()

    def _process_chunk(self, audio_chunk: np.ndarray):
        """Process a single audio chunk"""
        try:
            start_time = self.accumulated_audio_time
            chunk_duration = len(audio_chunk) / self.sample_rate

            logger.info(f"Processing chunk: {start_time:.1f}s - {start_time + chunk_duration:.1f}s")

            # Transcribe
            transcription = self.transcriber.transcribe(
                audio_chunk,
                self.sample_rate
            )

            # Diarize if available
            if self.diarizer:
                diarization = self.diarizer.diarize(
                    audio_chunk,
                    self.sample_rate
                )

                # Assign speakers to segments
                for segment in transcription.segments:
                    midpoint = (segment.start + segment.end) / 2
                    speaker_id = diarization.get_speaker_at_time(midpoint)
                    if speaker_id:
                        segment.speaker = speaker_id

            # Recognize speakers
            if self.voice_recognizer and len(self.known_speakers) > 0:
                self._recognize_speakers_in_segments(
                    audio_chunk,
                    transcription.segments
                )

            # Adjust segment times to global timeline
            for segment in transcription.segments:
                segment.start += start_time
                segment.end += start_time

            # Save to database
            if self.meeting_repo:
                for segment in transcription.segments:
                    transcript = Transcript(
                        transcript_id=None,
                        meeting_id=self.meeting_id,
                        text=segment.text,
                        start_time=segment.start,
                        end_time=segment.end,
                        speaker_id=segment.speaker,
                        confidence=segment.confidence
                    )
                    self.meeting_repo.add_transcript(transcript)

            # Call callbacks
            if self.transcript_callback:
                self.transcript_callback(transcription)

            # Update accumulated time
            self.accumulated_audio_time += chunk_duration

        except Exception as e:
            logger.error(f"Error processing chunk: {e}", exc_info=True)

    def _recognize_speakers_in_segments(self, audio_chunk: np.ndarray, segments):
        """Recognize speakers in transcription segments"""
        speaker_mapping = {}

        for segment in segments:
            if not segment.speaker or segment.speaker in speaker_mapping:
                continue

            # Extract segment audio
            start_sample = int(segment.start * self.sample_rate)
            end_sample = int(segment.end * self.sample_rate)

            if end_sample > len(audio_chunk):
                continue

            segment_audio = audio_chunk[start_sample:end_sample]

            # Skip if too short
            if len(segment_audio) < self.sample_rate * 0.5:  # Min 0.5s
                continue

            # Recognize
            result = self.voice_recognizer.recognize_speaker(
                segment_audio,
                self.sample_rate,
                self.known_speakers,
                threshold=0.7
            )

            if result.speaker_id:
                speaker_mapping[segment.speaker] = result.speaker_id

        # Apply mapping
        for segment in segments:
            if segment.speaker in speaker_mapping:
                segment.speaker = speaker_mapping[segment.speaker]

    def set_transcript_callback(self, callback: Callable):
        """
        Set callback for new transcriptions

        Args:
            callback: Function to call with TranscriptionResult
        """
        self.transcript_callback = callback

    def set_speaker_callback(self, callback: Callable):
        """
        Set callback for speaker events

        Args:
            callback: Function to call with speaker info
        """
        self.speaker_callback = callback

    def refresh_known_speakers(self):
        """Refresh known speakers from database"""
        if self.speaker_repo:
            self.known_speakers = self.speaker_repo.list_all()
            logger.info(f"Refreshed {len(self.known_speakers)} known speakers")

    def is_processing(self) -> bool:
        """Check if currently processing"""
        return self.processing
