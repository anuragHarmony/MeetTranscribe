# MeetTranscribe Dockerfile

FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    portaudio19-dev \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install WhisperX from GitHub
RUN pip install --no-cache-dir git+https://github.com/m-bain/whisperX.git

# Install Playwright browsers (optional, for meeting bot)
# RUN playwright install chromium

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/models data/speakers data/recordings data/exports logs

# Expose port (if adding web interface)
# EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run application
ENTRYPOINT ["python", "main.py"]
