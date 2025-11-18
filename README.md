# MeetTranscribe

**State-of-the-art meeting transcription system** with speaker diarization, voice recognition, and persistent speaker profiles.

## 🚀 Features

- **Multi-Source Audio Capture**: Microphone, system audio, dual capture, meeting bot integration
- **Advanced Speech-to-Text**: faster-whisper & WhisperX (70x realtime)
- **Speaker Diarization**: PyAnnote.audio 4.0 (SOTA 2025)
- **Voice Recognition**: ECAPA-TDNN embeddings with persistent speaker profiles
- **Database Persistence**: SQLite with speaker profiles and meeting records
- **Export Formats**: TXT, SRT, VTT, JSON

## 📋 Requirements

- Python 3.8+
- FFmpeg & PortAudio
- 4GB+ RAM (8GB+ recommended)
- GPU optional (CUDA for faster processing)

## 🔧 Installation

```bash
# Clone and setup
git clone https://github.com/yourusername/MeetTranscribe.git
cd MeetTranscribe
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install git+https://github.com/m-bain/whisperX.git
```

## 🎯 Quick Start

### Transcribe Audio File
```bash
python main.py transcribe meeting.wav --formats txt json srt
```

### Real-time Transcription
```bash
python main.py realtime --source dual --title "Team Meeting"
```

### Register Speaker
```bash
python main.py register "John Doe" sample.wav --email john@company.com
```

## 📖 Architecture

Modular design following SOLID principles:

```
src/
├── audio_capture/      # Microphone, system audio, dual capture
├── transcription/      # Whisper, WhisperX engines
├── diarization/        # PyAnnote speaker diarization
├── voice_recognition/  # SpeechBrain, WeSpeaker
├── database/           # SQLite persistence layer
├── meeting_bot/        # Playwright-based meeting bots
├── orchestration/      # Pipeline coordination
└── utils/              # Helpers and utilities
```

## ⚙️ Configuration

Edit `config/config.yaml`:

```yaml
transcription:
  engine: whisperx
  model_size: base
  device: auto

diarization:
  enabled: true
  model: pyannote/speaker-diarization-3.1

voice_recognition:
  enabled: true
  engine: speechbrain
  threshold: 0.7
```

## 📊 Performance

| Model | Speed | GPU Memory |
|-------|-------|------------|
| tiny | 32x RT | 1GB |
| base | 16x RT | 1GB |
| medium | 2x RT | 5GB |
| large-v3 | 1x RT | 10GB |

## 🐛 Troubleshooting

**Audio Capture (Linux):**
```bash
sudo apt-get install portaudio19-dev pulseaudio
```

**GPU Support:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

## 📄 License

MIT License

## 🙏 Acknowledgments

Built with OpenAI Whisper, PyAnnote.audio, SpeechBrain, faster-whisper, and WhisperX.

---

**State-of-the-art meeting transcription with speaker diarization and voice recognition**
