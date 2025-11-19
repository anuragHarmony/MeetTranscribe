# API Documentation

## Overview

MeetTranscribe provides both REST and WebSocket APIs for real-time meeting transcription.

## Base URL

```
http://localhost:8000
```

## REST Endpoints

### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy"
}
```

### List Voice Profiles

**GET** `/profiles`

Get all voice profiles.

**Response:**
```json
[
  {
    "profile_id": "uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "sample_count": 5,
    "created_at": "2024-01-01T00:00:00",
    "updated_at": "2024-01-01T00:00:00"
  }
]
```

### Get Voice Profile

**GET** `/profiles/{profile_id}`

Get specific voice profile.

**Response:**
```json
{
  "profile_id": "uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "sample_count": 5,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

### Delete Voice Profile

**DELETE** `/profiles/{profile_id}`

Delete a voice profile.

**Response:**
```json
{
  "status": "deleted",
  "profile_id": "uuid"
}
```

## WebSocket Endpoints

### Local Recording

**WebSocket** `/ws/local`

Real-time local audio transcription.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/local');
```

**Send:**
```json
{
  "capture_mode": "combined"
}
```

**Receive:**
```json
{
  "timestamp": "2024-01-01T00:00:00",
  "duration_ms": 10000,
  "source": "combined",
  "segments": [
    {
      "text": "Hello world",
      "start_time": 0.0,
      "end_time": 1.5,
      "confidence": 0.95,
      "speaker_id": "SPEAKER_00",
      "speaker_name": "John Doe",
      "speaker_email": "john@example.com"
    }
  ]
}
```

### Online Meeting

**WebSocket** `/ws/online`

Real-time online meeting transcription.

**Connect:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/online');
```

**Send:**
```json
{
  "platform": "google_meet",
  "meeting_url": "https://meet.google.com/xxx-xxxx-xxx",
  "credentials": {
    "email": "user@example.com",
    "password": "password"
  }
}
```

**Receive:**
```json
{
  "timestamp": "2024-01-01T00:00:00",
  "duration_ms": 10000,
  "source": "online_meeting",
  "segments": [
    {
      "text": "Hello everyone",
      "start_time": 0.0,
      "end_time": 2.0,
      "confidence": 0.98,
      "speaker_id": "SPEAKER_00",
      "speaker_name": "Jane Smith",
      "speaker_email": "jane@example.com"
    }
  ]
}
```

## Response Formats

### Transcription Result

```typescript
interface TranscriptionResult {
  timestamp: string;           // ISO 8601 timestamp
  duration_ms: number;          // Duration in milliseconds
  source: string;              // Audio source type
  segments: Segment[];         // Transcription segments
}

interface Segment {
  text: string;                // Transcribed text
  start_time: number;          // Start time in seconds
  end_time: number;            // End time in seconds
  confidence: number;          // Confidence score [0-1]
  speaker_id: string;          // Speaker ID from diarization
  speaker_name: string | null; // Identified speaker name
  speaker_email: string | null;// Identified speaker email
}
```

## Error Handling

### Error Response

```json
{
  "error": "Error message"
}
```

### Common Errors

| Error | Description |
|-------|-------------|
| `Service not initialized` | API not ready |
| `Profile not found` | Profile ID doesn't exist |
| `Missing platform or meeting_url` | Required fields missing |
| `Invalid capture mode` | Invalid audio capture mode |

## Rate Limiting

Currently no rate limiting implemented. Recommended for production:
- 100 requests/minute per IP
- WebSocket: 1 connection per user

## Authentication

Currently no authentication. Recommended for production:
- JWT tokens
- API keys
- OAuth 2.0

## CORS

CORS enabled for all origins by default. Configure in `config.yaml`:

```yaml
api:
  enable_cors: true
  allowed_origins: ["*"]
```

## Examples

### Python Client

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

### JavaScript Client

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/local');

ws.onopen = () => {
  ws.send(JSON.stringify({ capture_mode: 'combined' }));
};

ws.onmessage = (event) => {
  const result = JSON.parse(event.data);
  result.segments.forEach(segment => {
    console.log(`[${segment.speaker_name}] ${segment.text}`);
  });
};
```

### cURL

```bash
# Get profiles
curl http://localhost:8000/profiles

# Get specific profile
curl http://localhost:8000/profiles/{profile_id}

# Delete profile
curl -X DELETE http://localhost:8000/profiles/{profile_id}
```
