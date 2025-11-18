"""
MeetTranscribe setup script
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="meettranscribe",
    version="1.0.0",
    author="MeetTranscribe Team",
    description="State-of-the-art meeting transcription with speaker diarization and voice recognition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/meettranscribe",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "sounddevice>=0.4.6",
        "soundfile>=0.12.1",
        "librosa>=0.10.0",
        "faster-whisper>=0.10.0",
        "torch>=2.0.0",
        "torchaudio>=2.0.0",
        "pyannote.audio>=3.1.0",
        "pyannote.core>=5.0.0",
        "speechbrain>=0.5.16",
        "pyyaml>=6.0.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "bot": [
            "playwright>=1.40.0",
        ],
        "whisperx": [
            # Install WhisperX from GitHub
            # pip install git+https://github.com/m-bain/whisperX.git
        ],
    },
    entry_points={
        "console_scripts": [
            "meettranscribe=main:main",
        ],
    },
)
