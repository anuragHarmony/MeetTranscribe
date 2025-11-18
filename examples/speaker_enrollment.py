"""
Speaker enrollment example - register speakers for voice recognition
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.voice_recognition import SpeechBrainRecognizer
from src.voice_recognition.base import SpeakerProfile
from src.database import SQLiteDatabase, SpeakerRepository


def main():
    print("Speaker Enrollment System")
    print("=" * 80)

    # Initialize components
    recognizer = SpeechBrainRecognizer(device="auto")

    database = SQLiteDatabase("data/meettranscribe.db")
    database.connect()

    speaker_repo = SpeakerRepository(database)

    # Enroll speakers
    speakers_to_enroll = [
        {
            "id": "john_doe",
            "name": "John Doe",
            "email": "john@company.com",
            "audio_file": "path/to/john_sample.wav"
        },
        {
            "id": "jane_smith",
            "name": "Jane Smith",
            "email": "jane@company.com",
            "audio_file": "path/to/jane_sample.wav"
        }
    ]

    for speaker_data in speakers_to_enroll:
        print(f"\nEnrolling: {speaker_data['name']}")

        # Extract voice embedding
        embedding = recognizer.extract_embedding_from_file(
            speaker_data['audio_file']
        )

        # Create profile
        profile = SpeakerProfile(
            speaker_id=speaker_data['id'],
            name=speaker_data['name'],
            email=speaker_data['email'],
            embeddings=[embedding]
        )

        # Save to database
        speaker_repo.create(profile)

        print(f"✓ Enrolled: {speaker_data['name']} ({speaker_data['id']})")

    # List all enrolled speakers
    print("\n" + "=" * 80)
    print("Enrolled Speakers:")
    all_speakers = speaker_repo.list_all()

    for speaker in all_speakers:
        print(f"  - {speaker.name} ({speaker.speaker_id})")
        print(f"    Email: {speaker.email}")
        print(f"    Embeddings: {len(speaker.embeddings)}")

    database.disconnect()
    print("\n✓ Enrollment complete!")


if __name__ == "__main__":
    main()
