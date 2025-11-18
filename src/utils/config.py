"""
Configuration management
"""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import os


class Config:
    """
    Configuration manager for MeetTranscribe

    Loads configuration from YAML file and environment variables
    """

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load configuration from file"""
        config_file = Path(self.config_path)

        if config_file.exists():
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            self.config = self._get_default_config()

        # Override with environment variables
        self._load_env_overrides()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "audio": {
                "sample_rate": 16000,
                "channels": 1,
                "chunk_duration": 0.5
            },
            "transcription": {
                "engine": "whisperx",
                "model_size": "base",
                "device": "auto"
            },
            "diarization": {
                "enabled": True,
                "model": "pyannote/speaker-diarization-3.1",
                "device": "auto"
            },
            "voice_recognition": {
                "enabled": True,
                "engine": "speechbrain",
                "device": "auto",
                "threshold": 0.7
            },
            "database": {
                "type": "sqlite",
                "sqlite_path": "data/meettranscribe.db"
            },
            "logging": {
                "level": "INFO"
            }
        }

    def _load_env_overrides(self):
        """Load configuration overrides from environment variables"""
        # Example: MEETTRANSCRIBE_TRANSCRIPTION_MODEL_SIZE=large
        prefix = "MEETTRANSCRIBE_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix):].lower()

                # Split by underscore to get nested keys
                parts = config_key.split('_')

                # Navigate and set value
                current = self.config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set value (try to convert to appropriate type)
                current[parts[-1]] = self._convert_value(value)

    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type"""
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False

        # None/null
        if value.lower() in ('none', 'null'):
            return None

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String
        return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation

        Args:
            key: Configuration key (e.g., "transcription.model_size")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        parts = key.split('.')
        current = self.config

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    def set(self, key: str, value: Any):
        """
        Set configuration value using dot notation

        Args:
            key: Configuration key
            value: Value to set
        """
        parts = key.split('.')
        current = self.config

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    def save(self, path: Optional[str] = None):
        """
        Save configuration to file

        Args:
            path: Output path (uses config_path if not provided)
        """
        output_path = path or self.config_path
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    def __getitem__(self, key: str) -> Any:
        """Dictionary-style access"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        """Dictionary-style setting"""
        self.set(key, value)


# Global configuration instance
_config: Optional[Config] = None


def get_config(config_path: str = "config/config.yaml") -> Config:
    """
    Get global configuration instance

    Args:
        config_path: Path to configuration file

    Returns:
        Config instance
    """
    global _config

    if _config is None:
        _config = Config(config_path)

    return _config
