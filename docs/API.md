# MeetTranscribe REST API Documentation

## Overview

The MeetTranscribe API provides a RESTful interface for state-of-the-art meeting transcription as a service.

**Base URL**: `http://localhost:8000`
**API Docs**: `http://localhost:8000/docs` (Swagger UI)
**ReDoc**: `http://localhost:8000/redoc`

---

## Quick Start

### Start API Server

```bash
# Using Docker
docker-compose -f docker-compose.api.yml up

# Or directly with uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Test API

```bash
curl http://localhost:8000/health
```

---

## Endpoints

### Health Check

**GET** `/health`

Check API health and component status.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "components": {
    "transcriber": true,
    "diarizer": true,
    "voice_recognizer": true,
    "database": true,
    "vad": true
  }
}
```

---

### Transcribe Audio

**POST** `/transcribe`

Upload and transcribe an audio file.

**Parameters**:
- `file` (form-data, required): Audio file
- `language` (query, optional): Language code (e.g., 'en', 'es')
- `num_speakers` (query, optional): Number of speakers
- `enable_diarization` (query, default=true): Enable speaker diarization
- `enable_voice_recognition` (query, default=false): Enable voice recognition
- `use_vad` (query, default=true): Use voice activity detection

**Example**:

```bash
curl -X POST "http://localhost:8000/transcribe?language=en&use_vad=true" \
  -F "file=@meeting.wav"
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "progress": 0.0,
  "result": null,
  "error": null,
  "created_at": "2025-01-19T10:30:00",
  "completed_at": null
}
```

---

### Get Job Status

**GET** `/jobs/{job_id}`

Check transcription job status.

```bash
curl http://localhost:8000/jobs/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": 1.0,
  "result": {
    "meeting_id": "mtg_123456",
    "duration": 1234.5,
    "num_speakers": 3,
    "language": "en",
    "text": "Full transcription text...",
    "exports": {
      "txt": "/path/to/transcript.txt",
      "json": "/path/to/transcript.json",
      "srt": "/path/to/subtitles.srt",
      "vtt": "/path/to/subtitles.vtt"
    }
  },
  "error": null,
  "created_at": "2025-01-19T10:30:00",
  "completed_at": "2025-01-19T10:35:00"
}
```

---

### Download Transcription

**GET** `/jobs/{job_id}/download/{format}`

Download transcription in specified format (txt, json, srt, vtt).

```bash
curl -O http://localhost:8000/jobs/550e8400-e29b-41d4-a716-446655440000/download/txt
```

---

### Register Speaker

**POST** `/speakers/register`

Register a new speaker with voice sample.

**Parameters**:
- `file` (form-data, required): Audio sample file
- `speaker_id` (form-data, required): Unique speaker ID
- `name` (form-data, required): Speaker name
- `email` (form-data, optional): Speaker email

```bash
curl -X POST "http://localhost:8000/speakers/register" \
  -F "file=@john_sample.wav" \
  -F "speaker_id=john_doe" \
  -F "name=John Doe" \
  -F "email=john@company.com"
```

Response:
```json
{
  "status": "success",
  "speaker_id": "john_doe",
  "name": "John Doe",
  "email": "john@company.com"
}
```

---

### List Speakers

**GET** `/speakers`

List all registered speakers.

```bash
curl http://localhost:8000/speakers
```

Response:
```json
{
  "speakers": [
    {
      "speaker_id": "john_doe",
      "name": "John Doe",
      "email": "john@company.com",
      "embeddings_count": 3,
      "created_at": "2025-01-15T09:00:00"
    }
  ]
}
```

---

### List Meetings

**GET** `/meetings?limit=10`

List recent meetings.

```bash
curl "http://localhost:8000/meetings?limit=10"
```

Response:
```json
{
  "meetings": [
    {
      "meeting_id": "mtg_123456",
      "title": "Team Standup",
      "platform": "local",
      "duration": 1234.5,
      "start_time": "2025-01-19T10:00:00",
      "participants": ["john_doe", "jane_smith"]
    }
  ]
}
```

---

### Get Meeting Transcript

**GET** `/meetings/{meeting_id}/transcript`

Get full transcript for a specific meeting.

```bash
curl http://localhost:8000/meetings/mtg_123456/transcript
```

Response:
```json
{
  "meeting_id": "mtg_123456",
  "transcript": "[00:00:05] John Doe: Good morning everyone...\n[00:00:12] Jane Smith: Good morning!"
}
```

---

## Python Client Example

```python
import requests

# Upload file for transcription
with open("meeting.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/transcribe",
        files={"file": f},
        params={"language": "en", "use_vad": True}
    )

job = response.json()
job_id = job["job_id"]

# Poll for status
import time
while True:
    status_response = requests.get(f"http://localhost:8000/jobs/{job_id}")
    status = status_response.json()

    if status["status"] == "completed":
        print("Transcription complete!")
        print(f"Text: {status['result']['text']}")
        break
    elif status["status"] == "error":
        print(f"Error: {status['error']}")
        break

    time.sleep(2)

# Download result
txt_response = requests.get(f"http://localhost:8000/jobs/{job_id}/download/txt")
with open("transcript.txt", "wb") as f:
    f.write(txt_response.content)
```

---

## Error Handling

All endpoints return standard HTTP status codes:

- **200**: Success
- **400**: Bad Request
- **404**: Not Found
- **500**: Internal Server Error

Error response format:
```json
{
  "detail": "Error message"
}
```

---

## Rate Limiting

Currently no rate limiting (self-hosted). For production, consider adding nginx with rate limiting.

---

## Authentication

Currently no authentication (self-hosted, trusted network). For production, add:
- API keys
- JWT tokens
- OAuth2

---

## Deployment

### Production Configuration

```yaml
# docker-compose.api.yml
services:
  api:
    image: meettranscribe-api:latest
    environment:
      - WORKERS=4
      - LOG_LEVEL=warning
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Behind Nginx

```nginx
server {
    listen 80;
    server_name api.meettranscribe.local;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # For large file uploads
        client_max_body_size 500M;
    }
}
```

---

## Performance

- **Throughput**: ~10 concurrent jobs (depends on GPU)
- **Latency**: ~0.1x realtime (with GPU)
- **Max File Size**: 500MB (configurable)

---

## Monitoring

Access logs at:
- Console: Colored output with loguru
- File: `logs/api.log` (rotated, 10-day retention)

Monitor with:
```bash
tail -f logs/api.log
```

---

For more details, visit the interactive docs at `http://localhost:8000/docs`
