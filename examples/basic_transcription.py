"""
Basic audio file transcription example
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.transcription import WhisperXTranscriber
from src.diarization import PyAnnoteDiarizer
from src.orchestration import TranscriptionPipeline
from src.database import SQLiteDatabase
from src.utils import export_to_txt, export_to_json


def main():
    # Initialize components
    print("Initializing transcription pipeline...")

    transcriber = WhisperXTranscriber(
        model_size="base",
        device="auto"
    )

    diarizer = PyAnnoteDiarizer(
        model_name="pyannote/speaker-diarization-3.1"
    )

    database = SQLiteDatabase("data/meettranscribe.db")
    database.connect()

    # Create pipeline
    pipeline = TranscriptionPipeline(
        transcriber=transcriber,
        diarizer=diarizer,
        database=database
    )

    # Process audio file
    audio_file = "path/to/your/audio.wav"
    print(f"Processing: {audio_file}")

    result = pipeline.process_audio_file(
        audio_path=audio_file,
        language="en"  # or None for auto-detect
    )

    # Print results
    print("\n" + "=" * 80)
    print(f"Meeting ID: {result['meeting_id']}")
    print(f"Duration: {result['duration']:.1f} seconds")
    print(f"Speakers: {result['num_speakers']}")
    print("=" * 80)

    # Print transcription
    print("\nTranscription:")
    for segment in result['transcription'].segments:
        speaker = segment.speaker or "Unknown"
        print(f"[{speaker}] {segment.text}")

    # Export results
    export_to_txt(result['transcription'], "output.txt")
    export_to_json(result['transcription'], "output.json")
    print("\nExported to output.txt and output.json")

    # Clean up
    database.disconnect()


if __name__ == "__main__":
    main()
