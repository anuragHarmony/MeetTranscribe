# MeetTranscribe

State-of-the-art meeting transcription system with speaker identification and voice learning capabilities.

## Features

- **Real-time Speech-to-Text**: Uses OpenAI Whisper for accurate transcription
- **Dual Audio Capture Modes**:
  - Online meeting integration (Google Meet, Zoom, Teams, Slack Huddles)
  - Local recording (system audio + microphone)
- **Speaker Diarization**: Identifies who is speaking when using pyannote.audio
- **Voice Profile Learning**: Maintains persistent voice profiles across meetings
- **Speaker Identification**: Cross-references voices with organizational metadata using SpeechBrain
- **Modular Architecture**: Follows SOLID principles for extensibility
- **REST & WebSocket APIs**: Real-time transcription streaming
- **Self-Hosted**: Complete control over your data and privacy

## Quick Start

### Prerequisites

- Python 3.10+
- CUDA-capable GPU (recommended)
- FFmpeg and PortAudio
- HuggingFace account (for pyannote.audio)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/MeetTranscribe.git
cd MeetTranscribe

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your HUGGINGFACE_TOKEN
```

### Get HuggingFace Token

1. Create account at https://huggingface.co
2. Accept terms for pyannote.audio models
3. Create token at https://huggingface.co/settings/tokens
4. Add to `.env`: `HUGGINGFACE_TOKEN=your_token_here`

## Usage

### CLI

**Local Recording**
```bash
# Record with microphone and system audio
python cli.py record-local --mode combined

# Save to file
python cli.py record-local --mode combined --output transcript.json
```

**Online Meetings**
```bash
# Google Meet
python cli.py record-meeting \
  --platform google_meet \
  --url "https://meet.google.com/xxx-xxxx-xxx"

# Zoom
python cli.py record-meeting \
  --platform zoom \
  --url "https://zoom.us/j/123456789"
```

**API Server**
```bash
python cli.py serve
```

### Python API

**Local Recording**
```python
import asyncio
from src.transcription.service import TranscriptionService

async def main():
    service = TranscriptionService()
    await service.initialize()

    async for result in service.start_local_recording("combined"):
        for segment in result["segments"]:
            speaker = segment.get("speaker_name", "Unknown")
            print(f"[{speaker}] {segment['text']}")

    await service.stop()

asyncio.run(main())
```

**Online Meeting**
```python
async def main():
    service = TranscriptionService()
    await service.initialize()

    async for result in service.start_online_meeting(
        platform="google_meet",
        meeting_url="https://meet.google.com/xxx-xxxx-xxx"
    ):
        for segment in result["segments"]:
            speaker = segment.get("speaker_name", "Unknown")
            print(f"[{speaker}] {segment['text']}")

asyncio.run(main())
```

### WebSocket API

```python
import asyncio
import websockets
import json

async def transcribe():
    async with websockets.connect('ws://localhost:8000/ws/local') as ws:
        await ws.send(json.dumps({"capture_mode": "combined"}))

        while True:
            result = json.loads(await ws.recv())
            for segment in result["segments"]:
                print(f"[{segment['speaker_name']}] {segment['text']}")

asyncio.run(transcribe())
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         API Layer (FastAPI)                 │
│  REST │ WebSocket │ Health Checks           │
└─────────────────────────────────────────────┘
                    │
┌─────────────────────────────────────────────┐
│      TranscriptionService (Orchestrator)    │
└─────────────────────────────────────────────┘
    │           │           │           │
┌────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐
│ Audio  │ │Whisper  │ │ Speaker │ │Storage │
│Capture │ │ Engine  │ │ Module  │ │ Module │
└────────┘ └─────────┘ └─────────┘ └────────┘
```

### Project Structure

```
MeetTranscribe/
├── src/
│   ├── audio/              # Audio capture (local/system/combined)
│   ├── transcription/      # Whisper-based speech-to-text
│   ├── speaker/            # Diarization & identification
│   ├── platforms/          # Meeting platform integrations
│   ├── storage/            # Voice profile persistence
│   ├── api/                # FastAPI REST/WebSocket
│   └── core/               # Interfaces & config
├── config/                 # Configuration files
├── models/                 # ML model storage
├── data/                   # Voice profiles & meetings
├── examples/               # Usage examples
├── docs/                   # Documentation
└── tests/                  # Unit & integration tests
```

## Key Technologies

- **OpenAI Whisper**: State-of-the-art speech recognition
- **pyannote.audio**: Speaker diarization
- **SpeechBrain**: Speaker embeddings and identification
- **FastAPI**: Modern async web framework
- **Playwright**: Browser automation for meeting platforms
- **SQLAlchemy**: Database ORM for voice profiles
- **PyTorch**: Deep learning framework

## Configuration

Edit `config/config.yaml`:

```yaml
whisper:
  model_size: "medium"  # tiny, base, small, medium, large
  device: "cuda"        # cuda or cpu

speaker_recognition:
  similarity_threshold: 0.85
  min_samples_for_profile: 3

diarization:
  device: "cuda"
  min_speakers: null
  max_speakers: null
```

## Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## API Endpoints

### REST

- `GET /health` - Health check
- `GET /profiles` - List voice profiles
- `GET /profiles/{id}` - Get voice profile
- `DELETE /profiles/{id}` - Delete voice profile

### WebSocket

- `ws://localhost:8000/ws/local` - Local recording stream
- `ws://localhost:8000/ws/online` - Online meeting stream

See [API Documentation](docs/API.md) for details.

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and components
- [API Reference](docs/API.md) - REST and WebSocket API documentation
- [Usage Guide](docs/USAGE.md) - Detailed usage instructions

## Examples

See `examples/` directory:
- `local_recording.py` - Local audio transcription
- `online_meeting.py` - Join online meeting
- `create_voice_profile.py` - Create voice profiles
- `websocket_client.py` - WebSocket client example

## Features in Detail

### Audio Capture
- **Local Microphone**: Capture user's voice
- **System Audio**: Capture computer's audio output
- **Combined Mode**: Mix both sources (for local meetings)

### Speech Recognition
- **Whisper Models**: Choose accuracy vs speed
- **Multi-language**: Auto-detect or specify language
- **Real-time Streaming**: Process audio in chunks

### Speaker Diarization
- **Who Spoke When**: Segment audio by speaker
- **pyannote.audio**: State-of-the-art diarization
- **Configurable**: Set min/max speakers

### Speaker Identification
- **Voice Profiles**: Store voice embeddings
- **Persistent Learning**: Update profiles over time
- **Cross-reference**: Match voices to people
- **Metadata Integration**: Link to email/name from meetings

### Platform Integration
- **Google Meet**: Full support with metadata
- **Zoom**: Join and transcribe
- **Microsoft Teams**: Meeting support
- **Slack Huddles**: Workspace integration

## Performance

### Model Sizes

| Model  | Speed | Accuracy | VRAM   |
|--------|-------|----------|--------|
| tiny   | 32x   | Good     | ~1 GB  |
| base   | 16x   | Better   | ~1 GB  |
| small  | 6x    | Great    | ~2 GB  |
| medium | 2x    | Excellent| ~5 GB  |
| large  | 1x    | Best     | ~10 GB |

### Hardware Recommendations

- **CPU-only**: Use `tiny` or `base` models
- **GPU (4GB)**: Use `small` or `medium` models
- **GPU (8GB+)**: Use `medium` or `large` models

## Privacy & Security

- **Self-hosted**: All data stays on your infrastructure
- **No cloud**: No external API calls for transcription
- **Local storage**: Voice profiles stored locally
- **Configurable**: Control what data is saved

## Limitations

- **Browser automation**: May break with platform UI changes
- **Audio quality**: Depends on source quality
- **GPU recommended**: CPU-only is slower
- **Platform access**: Requires valid meeting credentials

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- OpenAI Whisper team
- pyannote.audio developers
- SpeechBrain project
- FastAPI framework

## Support

- Documentation: `docs/` directory
- Issues: GitHub Issues
- Examples: `examples/` directory

## Roadmap

- [ ] Real-time dashboard
- [ ] Multi-language support improvements
- [ ] Custom model fine-tuning
- [ ] Cloud storage integration
- [ ] Advanced analytics
- [ ] Mobile app support
