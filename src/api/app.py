"""FastAPI application for MeetTranscribe."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import get_config
from src.transcription.service import TranscriptionService

logger = logging.getLogger(__name__)

# Global service instance
service: Optional[TranscriptionService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    global service

    # Startup
    logger.info("Starting MeetTranscribe API")
    config = get_config()
    service = TranscriptionService(config)
    await service.initialize()
    logger.info("MeetTranscribe API started")

    yield

    # Shutdown
    logger.info("Shutting down MeetTranscribe API")
    if service:
        await service.stop()
    logger.info("MeetTranscribe API shut down")


# Create FastAPI app
app = FastAPI(
    title="MeetTranscribe API",
    description="State-of-the-art meeting transcription with speaker identification",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class StartLocalRecordingRequest(BaseModel):
    """Request to start local recording."""

    capture_mode: str = "combined"  # "mic", "system", or "combined"


class StartOnlineMeetingRequest(BaseModel):
    """Request to start online meeting."""

    platform: str  # "google_meet", "zoom", "teams", "slack"
    meeting_url: str
    credentials: Optional[Dict[str, str]] = None


class CreateVoiceProfileRequest(BaseModel):
    """Request to create voice profile."""

    name: str
    email: str
    # Audio samples would be uploaded separately


class VoiceProfileResponse(BaseModel):
    """Voice profile response."""

    profile_id: str
    name: Optional[str]
    email: Optional[str]
    sample_count: int
    created_at: str
    updated_at: str


# REST endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "MeetTranscribe API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/profiles")
async def list_profiles() -> List[VoiceProfileResponse]:
    """List all voice profiles."""
    if service is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    profiles = await service.storage.get_all_profiles()
    return [
        VoiceProfileResponse(
            profile_id=p.profile_id,
            name=p.name,
            email=p.email,
            sample_count=p.sample_count,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in profiles
    ]


@app.get("/profiles/{profile_id}")
async def get_profile(profile_id: str) -> VoiceProfileResponse:
    """Get voice profile by ID."""
    if service is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    profile = await service.storage.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    return VoiceProfileResponse(
        profile_id=profile.profile_id,
        name=profile.name,
        email=profile.email,
        sample_count=profile.sample_count,
        created_at=profile.created_at.isoformat(),
        updated_at=profile.updated_at.isoformat(),
    )


@app.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str):
    """Delete voice profile."""
    if service is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    await service.storage.delete_profile(profile_id)
    return {"status": "deleted", "profile_id": profile_id}


# WebSocket endpoints
@app.websocket("/ws/local")
async def websocket_local(websocket: WebSocket):
    """WebSocket endpoint for local recording."""
    await websocket.accept()

    if service is None:
        await websocket.send_json({"error": "Service not initialized"})
        await websocket.close()
        return

    logger.info("WebSocket connected: local recording")

    try:
        # Receive start request
        data = await websocket.receive_json()
        capture_mode = data.get("capture_mode", "combined")

        # Start recording
        async for result in service.start_local_recording(capture_mode):
            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})
    finally:
        await service.stop()
        try:
            await websocket.close()
        except Exception:
            pass


@app.websocket("/ws/online")
async def websocket_online(websocket: WebSocket):
    """WebSocket endpoint for online meetings."""
    await websocket.accept()

    if service is None:
        await websocket.send_json({"error": "Service not initialized"})
        await websocket.close()
        return

    logger.info("WebSocket connected: online meeting")

    try:
        # Receive start request
        data = await websocket.receive_json()
        platform = data.get("platform")
        meeting_url = data.get("meeting_url")
        credentials = data.get("credentials")

        if not platform or not meeting_url:
            await websocket.send_json(
                {"error": "Missing platform or meeting_url"}
            )
            await websocket.close()
            return

        # Start meeting
        async for result in service.start_online_meeting(
            platform, meeting_url, credentials
        ):
            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.send_json({"error": str(e)})
    finally:
        await service.stop()
        try:
            await websocket.close()
        except Exception:
            pass


# Logging setup
def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


if __name__ == "__main__":
    import uvicorn

    setup_logging()

    config = get_config()
    uvicorn.run(
        app,
        host=config.api.host,
        port=config.api.port,
        workers=config.api.workers,
    )
