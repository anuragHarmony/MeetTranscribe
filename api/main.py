"""
MeetTranscribe REST API

FastAPI-based REST API for meeting transcription as a service
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uuid
from pathlib import Path
import tempfile
import shutil
from datetime import datetime

# Loguru for better logging
from loguru import logger

# MeetTranscribe components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.transcription import WhisperXTranscriber, WhisperTranscriber
from src.diarization import PyAnnoteDiarizer
from src.voice_recognition import SpeechBrainRecognizer
from src.database import SQLiteDatabase, SpeakerRepository, MeetingRepository
from src.orchestration import TranscriptionPipeline
from src.utils import export_to_txt, export_to_json, export_to_srt, export_to_vtt
from src.utils.vad import SileroVAD

# Initialize FastAPI app
app = FastAPI(
    title="MeetTranscribe API",
    description="State-of-the-art meeting transcription with speaker diarization and voice recognition",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logger
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/api.log",
    rotation="500 MB",
    retention="10 days",
    level="DEBUG"
)

# Global components (initialized on startup)
transcriber = None
diarizer = None
voice_recognizer = None
database = None
pipeline = None
vad = None

# Job storage
jobs: Dict[str, Dict[str, Any]] = {}


# Pydantic models
class TranscribeRequest(BaseModel):
    language: Optional[str] = Field(None, description="Language code (e.g., 'en', 'es')")
    num_speakers: Optional[int] = Field(None, description="Number of speakers")
    enable_diarization: bool = Field(True, description="Enable speaker diarization")
    enable_voice_recognition: bool = Field(False, description="Enable voice recognition")
    use_vad: bool = Field(True, description="Use Voice Activity Detection")
    model_size: str = Field("base", description="Whisper model size")


class SpeakerRegisterRequest(BaseModel):
    speaker_id: str = Field(..., description="Unique speaker ID")
    name: str = Field(..., description="Speaker name")
    email: Optional[str] = Field(None, description="Speaker email")


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, error
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    global transcriber, diarizer, voice_recognizer, database, pipeline, vad

    logger.info("Starting MeetTranscribe API...")

    # Initialize transcriber
    logger.info("Loading speech-to-text model...")
    transcriber = WhisperXTranscriber(
        model_size="base",
        device="auto"
    )

    # Initialize diarizer
    logger.info("Loading speaker diarization model...")
    diarizer = PyAnnoteDiarizer(
        model_name="pyannote/speaker-diarization-3.1"
    )

    # Initialize voice recognizer
    logger.info("Loading voice recognition model...")
    voice_recognizer = SpeechBrainRecognizer(device="auto")

    # Initialize database
    logger.info("Connecting to database...")
    database = SQLiteDatabase("data/meettranscribe.db")
    database.connect()

    # Initialize VAD
    logger.info("Loading voice activity detection...")
    vad = SileroVAD(threshold=0.5)

    # Create pipeline
    pipeline = TranscriptionPipeline(
        transcriber=transcriber,
        diarizer=diarizer,
        voice_recognizer=voice_recognizer,
        database=database
    )

    logger.info("MeetTranscribe API ready!")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if database:
        database.disconnect()
    logger.info("MeetTranscribe API shutdowncompleted")


# Routes
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "MeetTranscribe API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "components": {
            "transcriber": transcriber is not None,
            "diarizer": diarizer is not None,
            "voice_recognizer": voice_recognizer is not None,
            "database": database is not None,
            "vad": vad is not None
        }
    }


@app.post("/transcribe", response_model=JobStatus)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: Optional[str] = None,
    num_speakers: Optional[int] = None,
    enable_diarization: bool = True,
    enable_voice_recognition: bool = False,
    use_vad: bool = True
):
    """
    Transcribe an audio file

    Returns a job ID for tracking progress
    """
    # Generate job ID
    job_id = str(uuid.uuid4())

    # Save uploaded file
    temp_dir = Path(tempfile.mkdtemp())
    audio_path = temp_dir / file.filename

    try:
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file")

    # Create job
    jobs[job_id] = {
        "job_id": job_id,
        "status": "pending",
        "progress": 0.0,
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "completed_at": None,
        "audio_path": str(audio_path),
        "temp_dir": str(temp_dir)
    }

    # Process in background
    background_tasks.add_task(
        process_transcription,
        job_id=job_id,
        audio_path=str(audio_path),
        language=language,
        num_speakers=num_speakers,
        enable_diarization=enable_diarization,
        enable_voice_recognition=enable_voice_recognition,
        use_vad=use_vad
    )

    logger.info(f"Created transcription job: {job_id}")

    return JobStatus(**jobs[job_id])


async def process_transcription(
    job_id: str,
    audio_path: str,
    language: Optional[str],
    num_speakers: Optional[int],
    enable_diarization: bool,
    enable_voice_recognition: bool,
    use_vad: bool
):
    """Background task for processing transcription"""
    try:
        # Update status
        jobs[job_id]["status"] = "processing"
        jobs[job_id]["progress"] = 0.1

        logger.info(f"Processing job {job_id}: {audio_path}")

        # Apply VAD if requested
        if use_vad and vad:
            logger.info(f"Applying VAD to job {job_id}")
            import soundfile as sf
            audio, sr = sf.read(audio_path, dtype='float32')
            filtered_audio, speech_segments = vad.filter_audio(audio)

            # Save filtered audio
            filtered_path = str(Path(audio_path).with_suffix('.filtered.wav'))
            sf.write(filtered_path, filtered_audio, sr)
            audio_path = filtered_path

            jobs[job_id]["progress"] = 0.2

        # Process with pipeline
        result = pipeline.process_audio_file(
            audio_path=audio_path,
            language=language,
            num_speakers=num_speakers if enable_diarization else None
        )

        jobs[job_id]["progress"] = 0.9

        # Export results
        export_dir = Path("data/exports") / job_id
        export_dir.mkdir(parents=True, exist_ok=True)

        exports = {}
        exports["txt"] = str(export_dir / "transcript.txt")
        exports["json"] = str(export_dir / "transcript.json")
        exports["srt"] = str(export_dir / "subtitles.srt")
        exports["vtt"] = str(export_dir / "subtitles.vtt")

        export_to_txt(result["transcription"], exports["txt"])
        export_to_json(result["transcription"], exports["json"])
        export_to_srt(result["transcription"], exports["srt"])
        export_to_vtt(result["transcription"], exports["vtt"])

        # Update job
        jobs[job_id].update({
            "status": "completed",
            "progress": 1.0,
            "result": {
                "meeting_id": result["meeting_id"],
                "duration": result["duration"],
                "num_speakers": result["num_speakers"],
                "language": result["transcription"].language,
                "text": result["transcription"].text,
                "exports": exports
            },
            "completed_at": datetime.now()
        })

        logger.info(f"Completed job {job_id}")

    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        jobs[job_id].update({
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now()
        })

    finally:
        # Cleanup temp files
        temp_dir = Path(jobs[job_id]["temp_dir"])
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatus(**jobs[job_id])


@app.get("/jobs/{job_id}/download/{format}")
async def download_result(job_id: str, format: str):
    """Download transcription result in specified format"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    if format not in job["result"]["exports"]:
        raise HTTPException(status_code=400, detail=f"Format '{format}' not available")

    file_path = job["result"]["exports"][format]

    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"transcript.{format}"
    )


@app.post("/speakers/register")
async def register_speaker(
    request: SpeakerRegisterRequest,
    file: UploadFile = File(...)
):
    """Register a new speaker with voice sample"""
    # Save audio file
    temp_dir = Path(tempfile.mkdtemp())
    audio_path = temp_dir / file.filename

    try:
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Register speaker
        profile = pipeline.register_speaker_from_audio(
            audio_path=str(audio_path),
            speaker_id=request.speaker_id,
            name=request.name,
            email=request.email
        )

        logger.info(f"Registered speaker: {request.speaker_id}")

        return {
            "status": "success",
            "speaker_id": profile.speaker_id,
            "name": profile.name,
            "email": profile.email
        }

    except Exception as e:
        logger.error(f"Failed to register speaker: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@app.get("/speakers")
async def list_speakers():
    """List all registered speakers"""
    speaker_repo = SpeakerRepository(database)
    speakers = speaker_repo.list_all()

    return {
        "speakers": [
            {
                "speaker_id": s.speaker_id,
                "name": s.name,
                "email": s.email,
                "embeddings_count": len(s.embeddings),
                "created_at": s.created_at.isoformat()
            }
            for s in speakers
        ]
    }


@app.get("/meetings")
async def list_meetings(limit: int = 10):
    """List recent meetings"""
    meeting_repo = MeetingRepository(database)
    meetings = meeting_repo.list_all()[:limit]

    return {
        "meetings": [
            {
                "meeting_id": m.meeting_id,
                "title": m.title,
                "platform": m.platform,
                "duration": m.duration,
                "start_time": m.start_time.isoformat(),
                "participants": m.participants
            }
            for m in meetings
        ]
    }


@app.get("/meetings/{meeting_id}/transcript")
async def get_meeting_transcript(meeting_id: str):
    """Get full transcript for a meeting"""
    meeting_repo = MeetingRepository(database)
    transcript = meeting_repo.get_full_transcript_text(meeting_id)

    if not transcript:
        raise HTTPException(status_code=404, detail="Meeting not found")

    return {
        "meeting_id": meeting_id,
        "transcript": transcript
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
