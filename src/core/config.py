"""Configuration management."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class AudioConfig:
    """Audio configuration."""
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 30  # 30ms chunks for VAD
    format: str = "int16"
    device_index: Optional[int] = None


@dataclass
class WhisperConfig:
    """Whisper model configuration."""
    model_size: str = "medium"  # tiny, base, small, medium, large
    device: str = "cuda"  # cuda or cpu
    language: Optional[str] = None  # None for auto-detect
    task: str = "transcribe"  # transcribe or translate
    compute_type: str = "float16"
    beam_size: int = 5
    best_of: int = 5
    temperature: float = 0.0


@dataclass
class DiarizationConfig:
    """Speaker diarization configuration."""
    model_name: str = "pyannote/speaker-diarization-3.1"
    device: str = "cuda"
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    segmentation_batch_size: int = 32


@dataclass
class SpeakerRecognitionConfig:
    """Speaker recognition configuration."""
    embedding_model: str = "speechbrain/spkrec-ecapa-voxceleb"
    similarity_threshold: float = 0.85
    device: str = "cuda"
    min_samples_for_profile: int = 3
    embedding_update_weight: float = 0.3  # Weight for incremental learning


@dataclass
class StorageConfig:
    """Storage configuration."""
    base_path: Path = field(default_factory=lambda: Path("data"))
    voice_profiles_path: Path = field(default_factory=lambda: Path("data/voice_profiles"))
    meetings_path: Path = field(default_factory=lambda: Path("data/meetings"))
    models_path: Path = field(default_factory=lambda: Path("models"))
    database_url: str = "sqlite:///data/meettranscribe.db"
    redis_url: Optional[str] = None


@dataclass
class PlatformConfig:
    """Meeting platform configuration."""
    google_meet: Dict[str, str] = field(default_factory=dict)
    zoom: Dict[str, str] = field(default_factory=dict)
    teams: Dict[str, str] = field(default_factory=dict)
    slack: Dict[str, str] = field(default_factory=dict)
    headless: bool = True
    timeout: int = 30


@dataclass
class APIConfig:
    """API configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    enable_cors: bool = True
    allowed_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class Config:
    """Main configuration class."""
    audio: AudioConfig = field(default_factory=AudioConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    diarization: DiarizationConfig = field(default_factory=DiarizationConfig)
    speaker_recognition: SpeakerRecognitionConfig = field(default_factory=SpeakerRecognitionConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    api: APIConfig = field(default_factory=APIConfig)

    @classmethod
    def from_yaml(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(config_path, "r") as f:
            config_dict = yaml.safe_load(f)

        return cls(
            audio=AudioConfig(**config_dict.get("audio", {})),
            whisper=WhisperConfig(**config_dict.get("whisper", {})),
            diarization=DiarizationConfig(**config_dict.get("diarization", {})),
            speaker_recognition=SpeakerRecognitionConfig(**config_dict.get("speaker_recognition", {})),
            storage=StorageConfig(**config_dict.get("storage", {})),
            platform=PlatformConfig(**config_dict.get("platform", {})),
            api=APIConfig(**config_dict.get("api", {})),
        )

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls(
            audio=AudioConfig(
                sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", 16000)),
                channels=int(os.getenv("AUDIO_CHANNELS", 1)),
            ),
            whisper=WhisperConfig(
                model_size=os.getenv("WHISPER_MODEL_SIZE", "medium"),
                device=os.getenv("WHISPER_DEVICE", "cuda"),
                language=os.getenv("WHISPER_LANGUAGE"),
            ),
            diarization=DiarizationConfig(
                device=os.getenv("DIARIZATION_DEVICE", "cuda"),
            ),
            speaker_recognition=SpeakerRecognitionConfig(
                device=os.getenv("SPEAKER_RECOGNITION_DEVICE", "cuda"),
                similarity_threshold=float(os.getenv("SIMILARITY_THRESHOLD", 0.85)),
            ),
            storage=StorageConfig(
                database_url=os.getenv("DATABASE_URL", "sqlite:///data/meettranscribe.db"),
                redis_url=os.getenv("REDIS_URL"),
            ),
        )

    def to_yaml(self, output_path: str) -> None:
        """Save configuration to YAML file."""
        config_dict = {
            "audio": vars(self.audio),
            "whisper": vars(self.whisper),
            "diarization": vars(self.diarization),
            "speaker_recognition": vars(self.speaker_recognition),
            "storage": {k: str(v) for k, v in vars(self.storage).items()},
            "platform": vars(self.platform),
            "api": vars(self.api),
        }

        with open(output_path, "w") as f:
            yaml.dump(config_dict, f, default_flow_style=False)


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance."""
    global _config
    if _config is None:
        config_path = os.getenv("CONFIG_PATH", "config/config.yaml")
        if os.path.exists(config_path):
            _config = Config.from_yaml(config_path)
        else:
            _config = Config.from_env()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance."""
    global _config
    _config = config
