"""
Export utilities for transcriptions
"""

import json
from typing import List
from pathlib import Path
from ..transcription.base import TranscriptionResult, Segment


def export_to_txt(transcription: TranscriptionResult, filepath: str) -> str:
    """
    Export transcription to plain text file

    Args:
        transcription: Transcription result
        filepath: Output file path

    Returns:
        Path to saved file
    """
    lines = []

    for segment in transcription.segments:
        timestamp = _format_timestamp(segment.start)
        speaker = segment.speaker or "Unknown"
        lines.append(f"[{timestamp}] {speaker}: {segment.text}")

    content = "\n".join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def export_to_srt(transcription: TranscriptionResult, filepath: str) -> str:
    """
    Export transcription to SRT subtitle format

    Args:
        transcription: Transcription result
        filepath: Output file path

    Returns:
        Path to saved file
    """
    lines = []

    for idx, segment in enumerate(transcription.segments, 1):
        # Sequence number
        lines.append(str(idx))

        # Timestamp
        start_time = _format_srt_timestamp(segment.start)
        end_time = _format_srt_timestamp(segment.end)
        lines.append(f"{start_time} --> {end_time}")

        # Text (with speaker if available)
        if segment.speaker:
            text = f"[{segment.speaker}] {segment.text}"
        else:
            text = segment.text
        lines.append(text)

        # Blank line
        lines.append("")

    content = "\n".join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def export_to_vtt(transcription: TranscriptionResult, filepath: str) -> str:
    """
    Export transcription to WebVTT format

    Args:
        transcription: Transcription result
        filepath: Output file path

    Returns:
        Path to saved file
    """
    lines = ["WEBVTT", ""]

    for idx, segment in enumerate(transcription.segments, 1):
        # Timestamp
        start_time = _format_vtt_timestamp(segment.start)
        end_time = _format_vtt_timestamp(segment.end)
        lines.append(f"{start_time} --> {end_time}")

        # Text (with speaker if available)
        if segment.speaker:
            text = f"<v {segment.speaker}>{segment.text}</v>"
        else:
            text = segment.text
        lines.append(text)

        # Blank line
        lines.append("")

    content = "\n".join(lines)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


def export_to_json(transcription: TranscriptionResult, filepath: str) -> str:
    """
    Export transcription to JSON format

    Args:
        transcription: Transcription result
        filepath: Output file path

    Returns:
        Path to saved file
    """
    data = {
        "text": transcription.text,
        "language": transcription.language,
        "duration": transcription.duration,
        "segments": []
    }

    for segment in transcription.segments:
        seg_data = {
            "text": segment.text,
            "start": segment.start,
            "end": segment.end,
            "speaker": segment.speaker,
            "confidence": segment.confidence,
            "words": []
        }

        for word in segment.words:
            word_data = {
                "text": word.text,
                "start": word.start,
                "end": word.end,
                "confidence": word.confidence
            }
            seg_data["words"].append(word_data)

        data["segments"].append(seg_data)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def _format_timestamp(seconds: float) -> str:
    """Format timestamp as HH:MM:SS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _format_srt_timestamp(seconds: float) -> str:
    """Format timestamp for SRT (HH:MM:SS,mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_vtt_timestamp(seconds: float) -> str:
    """Format timestamp for WebVTT (HH:MM:SS.mmm)"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
