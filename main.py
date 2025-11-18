"""
MeetTranscribe - State-of-the-art meeting transcription system

Main application entry point
"""

import logging
import argparse
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.utils.config import get_config
from src.audio_capture import MicrophoneCapture, SystemAudioCapture, DualAudioCapture
from src.transcription import WhisperTranscriber, WhisperXTranscriber
from src.diarization import PyAnnoteDiarizer
from src.voice_recognition import SpeechBrainRecognizer, WeSpeakerRecognizer
from src.database import SQLiteDatabase
from src.orchestration import TranscriptionPipeline, RealtimeProcessor
from src.utils import export_to_txt, export_to_srt, export_to_json, export_to_vtt


def setup_logging(config):
    """Setup logging configuration"""
    log_level = getattr(logging, config.get("logging.level", "INFO"))
    log_format = config.get(
        "logging.format",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create logs directory
    log_file = config.get("logging.file", "logs/meettranscribe.log")
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def create_transcriber(config):
    """Create transcription engine based on config"""
    engine = config.get("transcription.engine", "whisperx")
    model_size = config.get("transcription.model_size", "base")
    device = config.get("transcription.device", "auto")
    compute_type = config.get("transcription.compute_type", "auto")

    if engine == "whisperx":
        return WhisperXTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            batch_size=config.get("transcription.batch_size", 16)
        )
    else:
        return WhisperTranscriber(
            model_size=model_size,
            device=device,
            compute_type=compute_type
        )


def create_diarizer(config):
    """Create diarization engine based on config"""
    if not config.get("diarization.enabled", True):
        return None

    model = config.get("diarization.model", "pyannote/speaker-diarization-3.1")
    token = config.get("diarization.huggingface_token")
    device = config.get("diarization.device", "auto")

    return PyAnnoteDiarizer(
        model_name=model,
        use_auth_token=token,
        device=device
    )


def create_voice_recognizer(config):
    """Create voice recognition engine based on config"""
    if not config.get("voice_recognition.enabled", True):
        return None

    engine = config.get("voice_recognition.engine", "speechbrain")
    device = config.get("voice_recognition.device", "auto")

    if engine == "speechbrain":
        model = config.get(
            "voice_recognition.speechbrain_model",
            "speechbrain/spkrec-ecapa-voxceleb"
        )
        return SpeechBrainRecognizer(model_source=model, device=device)
    else:
        model = config.get(
            "voice_recognition.wespeaker_model",
            "wespeaker-voxceleb-resnet34-LM"
        )
        return WeSpeakerRecognizer(model_name=model, device=device)


def create_database(config):
    """Create database instance based on config"""
    db_type = config.get("database.type", "sqlite")

    if db_type == "sqlite":
        db_path = config.get("database.sqlite_path", "data/meettranscribe.db")
        db = SQLiteDatabase(db_path)
        db.connect()
        return db

    return None


def transcribe_file(args, config):
    """Transcribe an audio file"""
    logger = logging.getLogger(__name__)
    logger.info(f"Transcribing file: {args.input}")

    # Create components
    transcriber = create_transcriber(config)
    diarizer = create_diarizer(config)
    voice_recognizer = create_voice_recognizer(config)
    database = create_database(config)

    # Create pipeline
    pipeline = TranscriptionPipeline(
        transcriber=transcriber,
        diarizer=diarizer,
        voice_recognizer=voice_recognizer,
        database=database
    )

    # Process file
    result = pipeline.process_audio_file(
        audio_path=args.input,
        language=args.language,
        num_speakers=args.num_speakers
    )

    # Export results
    output_dir = Path(args.output or config.get("export.output_dir", "data/exports"))
    output_dir.mkdir(parents=True, exist_ok=True)

    base_name = Path(args.input).stem
    meeting_id = result["meeting_id"]

    # Export in requested formats
    formats = args.formats or config.get("export.default_formats", ["txt", "json"])

    for fmt in formats:
        output_file = output_dir / f"{base_name}_{meeting_id[:8]}.{fmt}"

        if fmt == "txt":
            export_to_txt(result["transcription"], str(output_file))
        elif fmt == "srt":
            export_to_srt(result["transcription"], str(output_file))
        elif fmt == "vtt":
            export_to_vtt(result["transcription"], str(output_file))
        elif fmt == "json":
            export_to_json(result["transcription"], str(output_file))

        logger.info(f"Exported to: {output_file}")

    logger.info("Transcription complete!")
    print(f"\nMeeting ID: {meeting_id}")
    print(f"Duration: {result['duration']:.1f}s")
    print(f"Speakers: {result['num_speakers']}")


def realtime_transcribe(args, config):
    """Real-time transcription from microphone/system audio"""
    logger = logging.getLogger(__name__)
    logger.info("Starting real-time transcription...")

    # Create audio capture
    sample_rate = config.get("audio.sample_rate", 16000)
    chunk_duration = config.get("audio.chunk_duration", 0.5)

    if args.source == "microphone":
        audio_capture = MicrophoneCapture(
            sample_rate=sample_rate,
            chunk_duration=chunk_duration
        )
    elif args.source == "system":
        audio_capture = SystemAudioCapture(
            sample_rate=sample_rate,
            chunk_duration=chunk_duration
        )
    else:  # dual
        audio_capture = DualAudioCapture(
            sample_rate=sample_rate,
            chunk_duration=chunk_duration
        )

    # Create components
    transcriber = create_transcriber(config)
    diarizer = create_diarizer(config)
    voice_recognizer = create_voice_recognizer(config)
    database = create_database(config)

    # Create realtime processor
    processor = RealtimeProcessor(
        audio_capture=audio_capture,
        transcriber=transcriber,
        diarizer=diarizer,
        voice_recognizer=voice_recognizer,
        database=database,
        chunk_duration=config.get("realtime.chunk_duration", 10.0),
        overlap=config.get("realtime.overlap", 2.0)
    )

    # Set callback to print transcriptions
    def on_transcript(transcription):
        print("\n" + "=" * 80)
        for segment in transcription.segments:
            speaker = segment.speaker or "Unknown"
            print(f"[{speaker}] {segment.text}")
        print("=" * 80)

    processor.set_transcript_callback(on_transcript)

    # Start processing
    try:
        processor.start(meeting_title=args.title or "Live Meeting")

        print("\n🎙️  Real-time transcription started!")
        print("Press Ctrl+C to stop...\n")

        # Keep running until interrupted
        import time
        while processor.is_processing():
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
        processor.stop()

        meeting_id = processor.meeting_id
        print(f"\nMeeting saved: {meeting_id}")

        # Export if requested
        if args.export and database:
            from src.database import MeetingRepository
            meeting_repo = MeetingRepository(database)
            transcript_text = meeting_repo.get_full_transcript_text(meeting_id)

            if transcript_text:
                output_dir = Path(config.get("export.output_dir", "data/exports"))
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"meeting_{meeting_id[:8]}.txt"

                with open(output_file, 'w') as f:
                    f.write(transcript_text)

                print(f"Transcript exported to: {output_file}")


def register_speaker(args, config):
    """Register a new speaker"""
    logger = logging.getLogger(__name__)
    logger.info(f"Registering speaker: {args.name}")

    # Create components
    voice_recognizer = create_voice_recognizer(config)
    database = create_database(config)

    if not voice_recognizer or not database:
        print("Error: Voice recognition and database required for speaker registration")
        return

    # Create pipeline (needed for registration)
    from src.transcription import WhisperTranscriber
    transcriber = WhisperTranscriber(model_size="base")

    pipeline = TranscriptionPipeline(
        transcriber=transcriber,
        voice_recognizer=voice_recognizer,
        database=database
    )

    # Register speaker
    profile = pipeline.register_speaker_from_audio(
        audio_path=args.audio,
        speaker_id=args.id or args.name.lower().replace(" ", "_"),
        name=args.name,
        email=args.email
    )

    print(f"\n✓ Speaker registered successfully!")
    print(f"  ID: {profile.speaker_id}")
    print(f"  Name: {profile.name}")
    print(f"  Email: {profile.email}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="MeetTranscribe - State-of-the-art meeting transcription"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Transcribe file command
    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe an audio file"
    )
    transcribe_parser.add_argument("input", help="Input audio file")
    transcribe_parser.add_argument("-o", "--output", help="Output directory")
    transcribe_parser.add_argument("-l", "--language", help="Language code (e.g., en, es)")
    transcribe_parser.add_argument("-s", "--num-speakers", type=int, help="Number of speakers")
    transcribe_parser.add_argument(
        "-f", "--formats",
        nargs="+",
        choices=["txt", "srt", "vtt", "json"],
        help="Export formats"
    )

    # Real-time transcription command
    realtime_parser = subparsers.add_parser(
        "realtime",
        help="Real-time transcription"
    )
    realtime_parser.add_argument(
        "--source",
        choices=["microphone", "system", "dual"],
        default="dual",
        help="Audio source"
    )
    realtime_parser.add_argument("--title", help="Meeting title")
    realtime_parser.add_argument("--export", action="store_true", help="Export transcript after recording")

    # Register speaker command
    register_parser = subparsers.add_parser(
        "register",
        help="Register a new speaker"
    )
    register_parser.add_argument("name", help="Speaker name")
    register_parser.add_argument("audio", help="Audio sample file")
    register_parser.add_argument("--id", help="Speaker ID (auto-generated if not provided)")
    register_parser.add_argument("--email", help="Speaker email")

    # Parse arguments
    args = parser.parse_args()

    # Load configuration
    config = get_config()

    # Setup logging
    setup_logging(config)

    # Execute command
    if args.command == "transcribe":
        transcribe_file(args, config)
    elif args.command == "realtime":
        realtime_transcribe(args, config)
    elif args.command == "register":
        register_speaker(args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
