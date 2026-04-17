"""
Seed Test — Add Voices
======================
Uploads every .wav file found in tests/voice_samples into the voice library.

Standard voices (is_standard=True) are identified by a STANDARD_VOICES set below.
Everything else is uploaded as a non-standard character voice.

Run from the project root:
    python -m tests.test_add_voices
"""

import asyncio
import io
import os
from pathlib import Path

from tests.client_factory import get_clients
from app.services.voice_library import VoiceLibraryManager

# ---------------------------------------------------------------------------
# Filenames (without path) that should be flagged as standard narrator voices.
# These are safe, neutral, low-pizzazz reads suitable for narrator assignment.
# Add or remove names here as your library grows.
# ---------------------------------------------------------------------------
STANDARD_VOICES = {
    "woman_voice_sample.wav",
}

VOICES_DIR = Path(__file__).resolve().parent / "voice_samples"


async def test_add_voice_batch():
    # Setup
    collection, r2_session, r2_config = get_clients()
    manager = VoiceLibraryManager(collection, r2_session, r2_config)

    print("🚀 Starting 'Add Voice' seed test...")
    print(f"   Looking in: {VOICES_DIR}\n")

    if not VOICES_DIR.exists():
        print(f"❌ Directory not found: {VOICES_DIR}")
        return

    voice_files = sorted(VOICES_DIR.glob("*.wav"))

    if not voice_files:
        print(f"❌ No .wav files found in {VOICES_DIR}")
        return

    print(f"Found {len(voice_files)} file(s). Uploading...\n")

    results = {"ok": [], "failed": []}

    for wav_path in voice_files:
        filename = wav_path.name
        is_standard = filename in STANDARD_VOICES
        flag_label = "🌟 STANDARD" if is_standard else "🎭 character"

        print(f"--- {filename}  [{flag_label}] ---")

        try:
            with open(wav_path, "rb") as f:
                audio_stream = io.BytesIO(f.read())

            voice_id = await manager.add_voice(
                input_audio=audio_stream,
                filename=filename,
                start_time="00:00",
                is_standard=is_standard,
            )

            print(f"✅ Uploaded  →  {voice_id}\n")
            results["ok"].append((filename, voice_id))

        except Exception as e:
            print(f"❌ Failed: {e}\n")
            import traceback
            traceback.print_exc()
            results["failed"].append(filename)

    # Summary
    print("=" * 50)
    print(f"✅ {len(results['ok'])} uploaded successfully")
    if results["failed"]:
        print(f"❌ {len(results['failed'])} failed: {results['failed']}")
    print("=" * 50)

    if results["ok"]:
        print("\nSeeded voice IDs:")
        for name, vid in results["ok"]:
            marker = "🌟" if name in STANDARD_VOICES else "  "
            print(f"  {marker} {name}  →  {vid}")


if __name__ == "__main__":
    asyncio.run(test_add_voice_batch())