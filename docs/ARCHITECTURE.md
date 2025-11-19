# Architecture

## Overview

MeetTranscribe is a state-of-the-art meeting transcription system built with modularity and SOLID principles. It provides real-time speech-to-text transcription with speaker identification and voice learning capabilities.

## System Components

### 1. Audio Capture Module (`src/audio/`)

Handles audio input from multiple sources:
- **LocalAudioCapture**: Captures microphone input
- **SystemAudioCapture**: Captures system audio output
- **CombinedAudioCapture**: Mixes both sources

**Key Features:**
- Asynchronous audio streaming
- Configurable sample rates and chunk sizes
- Queue-based buffering

### 2. Transcription Module (`src/transcription/`)

Converts speech to text using state-of-the-art models:
- **WhisperTranscriptionEngine**: OpenAI Whisper integration
- **TranscriptionService**: Main orchestrator

**Key Features:**
- Real-time and batch transcription
- Multiple language support
- Streaming API for continuous transcription

### 3. Speaker Module (`src/speaker/`)

Identifies and tracks speakers:
- **PyAnnoteDiarization**: Speaker diarization using pyannote.audio
- **SpeechBrainIdentification**: Voice embedding and speaker recognition

**Key Features:**
- Speaker segmentation (who spoke when)
- Voice profile creation and matching
- Incremental learning from new samples

### 4. Platform Integration Module (`src/platforms/`)

Integrates with meeting platforms:
- **GoogleMeetIntegration**: Google Meet support
- **ZoomIntegration**: Zoom support
- **TeamsIntegration**: Microsoft Teams support
- **SlackIntegration**: Slack Huddles support

**Key Features:**
- Browser automation using Playwright
- Metadata extraction (participants, meeting info)
- Audio stream capture

### 5. Storage Module (`src/storage/`)

Manages persistent data:
- **VoiceProfileStorage**: SQLite + file-based storage
- Voice embeddings stored as numpy arrays
- Metadata in relational database

**Key Features:**
- Async database operations
- Profile CRUD operations
- Incremental learning support

### 6. API Module (`src/api/`)

Provides REST and WebSocket interfaces:
- **FastAPI application**: REST endpoints
- **WebSocket endpoints**: Real-time streaming

**Key Features:**
- CORS support
- Health checks
- Profile management API

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                     │
│  REST Endpoints │ WebSocket Endpoints │ Health Checks        │
└─────────────────────────────────────────────────────────────┘
                            │
┌─────────────────────────────────────────────────────────────┐
│                  TranscriptionService                        │
│         (Main Orchestrator - Business Logic)                 │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
    ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Audio  │   │Transcribe│   │ Speaker  │   │ Storage  │
    │Capture │   │  Engine  │   │  Module  │   │  Module  │
    └────────┘   └──────────┘   └──────────┘   └──────────┘
         │              │              │              │
    ┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
    │Local/  │   │ Whisper  │   │pyannote/ │   │SQLite +  │
    │Platform│   │  Model   │   │SpeechBrain│   │ Files   │
    └────────┘   └──────────┘   └──────────┘   └──────────┘
```

## Data Flow

### Local Recording Flow

1. **Audio Capture**: LocalAudioCapture/CombinedAudioCapture captures audio
2. **Audio Stream**: Chunks streamed to TranscriptionService
3. **Transcription**: WhisperEngine transcribes audio
4. **Diarization**: PyAnnote identifies speaker segments
5. **Identification**: SpeechBrain matches speakers to profiles
6. **Learning**: Profiles updated with new samples
7. **Output**: Results streamed to client

### Online Meeting Flow

1. **Platform Connection**: Browser automation connects to meeting
2. **Metadata Extraction**: Participant info extracted
3. **Audio Capture**: Meeting audio captured
4. **Processing**: Same as local recording (steps 3-7)
5. **Profile Creation**: New profiles created for participants

## SOLID Principles

### Single Responsibility Principle
- Each module has one clear purpose
- Audio capture separate from transcription
- Diarization separate from identification

### Open/Closed Principle
- Interfaces allow new implementations
- Easy to add new platforms
- Easy to swap ML models

### Liskov Substitution Principle
- All capture implementations use IAudioCapture
- All transcription engines use ITranscriptionEngine
- Implementations are interchangeable

### Interface Segregation Principle
- Specific interfaces for specific needs
- IAudioCapture vs ITranscriptionEngine
- No "god interface"

### Dependency Inversion Principle
- Depend on abstractions (interfaces)
- TranscriptionService depends on interfaces
- Concrete implementations injected

## Configuration

Configuration managed through:
- **YAML files**: `config/config.yaml`
- **Environment variables**: `.env`
- **Code**: `Config` dataclass

Hierarchical configuration:
1. Default values in code
2. YAML file overrides
3. Environment variable overrides

## Storage Architecture

### Voice Profiles
- **Embeddings**: Stored as `.npy` files
- **Metadata**: SQLite database
- **Profile ID**: UUID for unique identification

### Database Schema
```sql
CREATE TABLE voice_profiles (
    id INTEGER PRIMARY KEY,
    profile_id VARCHAR(255) UNIQUE,
    name VARCHAR(255),
    email VARCHAR(255),
    embedding_path VARCHAR(512),
    sample_count INTEGER,
    created_at DATETIME,
    updated_at DATETIME,
    metadata_json TEXT
);
```

## Scalability

### Current Design
- Single-process, async I/O
- In-memory audio buffering
- File-based voice embeddings

### Future Scaling Options
1. **Multi-process**: Process pool for ML models
2. **Distributed**: Redis for shared state
3. **Cloud Storage**: S3 for embeddings
4. **Database**: PostgreSQL for metadata
5. **Message Queue**: RabbitMQ for audio streaming

## Performance Considerations

### Bottlenecks
1. **Whisper inference**: GPU recommended
2. **Speaker diarization**: GPU recommended
3. **Audio I/O**: Async operations critical

### Optimizations
- Batch processing for efficiency
- GPU acceleration for ML models
- Async I/O throughout
- Streaming API to reduce latency

## Security Considerations

1. **Credentials**: Never logged or exposed
2. **Audio Data**: Processed in-memory, not persisted
3. **Voice Profiles**: Access control needed
4. **API**: Authentication recommended for production
5. **Platform Integration**: Headless browser sandboxing

## Testing Strategy

### Unit Tests
- Test each module independently
- Mock dependencies
- Test interfaces

### Integration Tests
- Test component interaction
- Test with real audio samples
- Test database operations

### End-to-End Tests
- Test full workflow
- Test with mock meetings
- Test API endpoints

## Deployment

### Development
```bash
python cli.py record-local --mode combined
```

### Production (Docker)
```bash
docker-compose up -d
```

### Production (Kubernetes)
- Helm chart (future)
- Auto-scaling based on CPU/GPU
- Persistent volumes for storage
