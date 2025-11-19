# Usage Guide

## Installation

### Prerequisites

- Python 3.10+
- CUDA-capable GPU (recommended for better performance)
- FFmpeg
- PortAudio

### Install Dependencies

```bash
# Clone repository
git clone https://github.com/yourusername/MeetTranscribe.git
cd MeetTranscribe

# Install Python dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your HUGGINGFACE_TOKEN
```

### HuggingFace Token

pyannote.audio requires a HuggingFace token:

1. Create account at https://huggingface.co
2. Accept terms for pyannote models
3. Create token at https://huggingface.co/settings/tokens
4. Add to `.env`: `HUGGINGFACE_TOKEN=your_token_here`

## Configuration

### Config File

Edit `config/config.yaml`:

```yaml
whisper:
  model_size: "medium"  # tiny, base, small, medium, large
  device: "cuda"        # cuda or cpu

speaker_recognition:
  similarity_threshold: 0.85  # Adjust for sensitivity
```

### Environment Variables

Set in `.env`:

```bash
WHISPER_MODEL_SIZE=medium
WHISPER_DEVICE=cuda
SIMILARITY_THRESHOLD=0.85
```

## CLI Usage

### Local Recording

Record and transcribe local audio:

```bash
# Microphone only
python cli.py record-local --mode mic

# Combined (mic + system audio)
python cli.py record-local --mode combined

# Save to file
python cli.py record-local --mode combined --output output.json
```

### Online Meetings

Join and transcribe online meetings:

```bash
# Google Meet
python cli.py record-meeting \
  --platform google_meet \
  --url "https://meet.google.com/xxx-xxxx-xxx"

# With credentials
python cli.py record-meeting \
  --platform google_meet \
  --url "https://meet.google.com/xxx-xxxx-xxx" \
  --email "your@email.com" \
  --password "your_password"

# Zoom
python cli.py record-meeting \
  --platform zoom \
  --url "https://zoom.us/j/123456789"

# Microsoft Teams
python cli.py record-meeting \
  --platform teams \
  --url "https://teams.microsoft.com/..."

# Slack Huddle
python cli.py record-meeting \
  --platform slack \
  --url "https://app.slack.com/..."
```

### Voice Profile Management

```bash
# List profiles
python cli.py list-profiles

# Delete profile
python cli.py delete-profile --profile-id "uuid"
```

### Start API Server

```bash
python cli.py serve
```

## Python API Usage

### Local Recording

```python
import asyncio
from src.core.config import Config
from src.transcription.service import TranscriptionService

async def main():
    config = Config()
    service = TranscriptionService(config)
    await service.initialize()

    async for result in service.start_local_recording("combined"):
        for segment in result["segments"]:
            print(f"[{segment['speaker_name']}] {segment['text']}")

    await service.stop()

asyncio.run(main())
```

### Online Meeting

```python
import asyncio
from src.transcription.service import TranscriptionService

async def main():
    service = TranscriptionService()
    await service.initialize()

    async for result in service.start_online_meeting(
        platform="google_meet",
        meeting_url="https://meet.google.com/xxx-xxxx-xxx",
        credentials={"email": "...", "password": "..."}
    ):
        for segment in result["segments"]:
            print(f"[{segment['speaker_name']}] {segment['text']}")

    await service.stop()

asyncio.run(main())
```

### Create Voice Profile

```python
import asyncio
from src.transcription.service import TranscriptionService
from src.core.interfaces import AudioChunk

async def main():
    service = TranscriptionService()
    await service.initialize()

    # Collect audio samples (minimum 3)
    audio_samples = []  # List of AudioChunk objects

    profile = await service.create_voice_profile(
        name="John Doe",
        email="john@example.com",
        audio_samples=audio_samples
    )

    print(f"Created profile: {profile.profile_id}")

asyncio.run(main())
```

## WebSocket Usage

### Python Client

```python
import asyncio
import websockets
import json

async def transcribe():
    uri = "ws://localhost:8000/ws/local"

    async with websockets.connect(uri) as ws:
        # Start recording
        await ws.send(json.dumps({"capture_mode": "combined"}))

        # Receive transcriptions
        while True:
            message = await ws.recv()
            result = json.loads(message)

            for segment in result["segments"]:
                speaker = segment.get("speaker_name", "Unknown")
                print(f"[{speaker}] {segment['text']}")

asyncio.run(transcribe())
```

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/local');

ws.onopen = () => {
  ws.send(JSON.stringify({ capture_mode: 'combined' }));
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);

  result.segments.forEach(segment => {
    const speaker = segment.speaker_name || 'Unknown';
    console.log(`[${speaker}] ${segment.text}`);
  });
};
```

## Docker Usage

### Build and Run

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Access API

```bash
curl http://localhost:8000/health
```

## Best Practices

### Audio Quality

- Use good quality microphone
- Minimize background noise
- Ensure clear audio (16kHz+)

### Voice Profiles

- Collect 3-5 high-quality samples
- Use varied speech samples
- Update profiles over time

### Performance

- Use GPU for better speed
- Adjust model size based on accuracy needs
- Monitor memory usage

### Security

- Never commit credentials
- Use environment variables
- Implement authentication in production

## Troubleshooting

### No Audio Captured

- Check device permissions
- Verify audio device index
- Test with system audio tools

### Poor Transcription Quality

- Increase Whisper model size
- Improve audio quality
- Check language settings

### Speaker Identification Issues

- Collect more voice samples
- Adjust similarity threshold
- Verify profile quality

### Platform Integration Fails

- Check meeting URL format
- Verify credentials
- Review browser logs

### GPU Not Used

- Install CUDA toolkit
- Verify PyTorch CUDA support
- Check `device` in config

## Performance Tips

1. **Model Selection**
   - `tiny`: Fastest, lower accuracy
   - `base`: Good balance
   - `medium`: Better accuracy
   - `large`: Best accuracy, slowest

2. **Hardware**
   - GPU: 10-20x faster
   - RAM: 8GB+ recommended
   - CPU: Multi-core beneficial

3. **Configuration**
   - Adjust chunk duration
   - Tune buffer sizes
   - Optimize batch processing

## Advanced Usage

### Custom Configuration

```python
from src.core.config import Config, WhisperConfig

config = Config()
config.whisper = WhisperConfig(
    model_size="large",
    device="cuda",
    language="en"
)

service = TranscriptionService(config)
```

### Custom Audio Source

```python
from src.core.interfaces import IAudioCapture

class CustomAudioCapture(IAudioCapture):
    # Implement interface methods
    pass

# Use custom capture
service = TranscriptionService()
service.audio_capture = CustomAudioCapture()
```

### Batch Processing

```python
# Process multiple audio files
for audio_file in audio_files:
    audio_data = load_audio(audio_file)
    chunk = AudioChunk(...)
    segments = await service.transcription_engine.transcribe(chunk)
```
