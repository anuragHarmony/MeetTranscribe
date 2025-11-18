"""
Real-time transcription example with live audio capture
"""

import sys
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.audio_capture import DualAudioCapture
from src.transcription import WhisperXTranscriber
from src.diarization import PyAnnoteDiarizer
from src.voice_recognition import SpeechBrainRecognizer
from src.orchestration import RealtimeProcessor
from src.database import SQLiteDatabase


def main():
    print("Real-time Meeting Transcription")
    print("=" * 80)

    # Initialize components
    print("Initializing...")

    # Audio capture (dual: microphone + system audio)
    audio_capture = DualAudioCapture(
        sample_rate=16000,
        chunk_duration=0.5
    )

    # Transcriber
    transcriber = WhisperXTranscriber(
        model_size="base",
        device="auto"
    )

    # Diarizer (optional)
    diarizer = PyAnnoteDiarizer(
        model_name="pyannote/speaker-diarization-3.1"
    )

    # Voice recognizer (optional)
    voice_recognizer = SpeechBrainRecognizer(device="auto")

    # Database
    database = SQLiteDatabase("data/meettranscribe.db")
    database.connect()

    # Create real-time processor
    processor = RealtimeProcessor(
        audio_capture=audio_capture,
        transcriber=transcriber,
        diarizer=diarizer,
        voice_recognizer=voice_recognizer,
        database=database,
        chunk_duration=10.0,
        overlap=2.0
    )

    # Set callback to print transcriptions
    def on_transcript(transcription):
        print("\n" + "=" * 80)
        for segment in transcription.segments:
            speaker = segment.speaker or "Unknown"
            timestamp = f"{segment.start:.1f}s"
            print(f"[{timestamp}] {speaker}: {segment.text}")
        print("=" * 80)

    processor.set_transcript_callback(on_transcript)

    # Start processing
    try:
        print("\n🎙️  Starting real-time transcription...")
        print("Press Ctrl+C to stop\n")

        processor.start(meeting_title="Live Meeting")

        # Keep running
        while processor.is_processing():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
        processor.stop()

        meeting_id = processor.meeting_id
        print(f"\n✓ Meeting saved: {meeting_id}")

        # Get full transcript
        from src.database import MeetingRepository
        meeting_repo = MeetingRepository(database)
        transcript = meeting_repo.get_full_transcript_text(meeting_id)

        # Save to file
        output_file = f"meeting_{meeting_id[:8]}.txt"
        with open(output_file, 'w') as f:
            f.write(transcript)

        print(f"✓ Transcript saved to: {output_file}")

    finally:
        database.disconnect()


if __name__ == "__main__":
    main()
