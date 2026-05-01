"""
Seed Standard Voices
====================
1. Clears the entire voice_library MongoDB collection
2. Deletes all objects under voice_library/ in R2
3. Re-uploads every .wav in tests/voice_samples through VoiceLibraryManager
   (full pipeline: clean audio → Whisper description → embed → R2 → Mongo)

STANDARD_VOICES below controls which filenames get is_standard=True.

Run from the ai-service root:
    python -m tests.seed_standard_voices
"""

import asyncio
import io
from pathlib import Path

import aioboto3
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config_settings import settings
from app.services.voice_library import VoiceLibraryManager
from tests.client_factory import get_clients

# ---------------------------------------------------------------------------
# Which filenames should be flagged as standard narrator voices
# ---------------------------------------------------------------------------
STANDARD_VOICES = {
    "woman_voice_sample.wav",
}

VOICES_DIR = Path(__file__).resolve().parent / "voice_samples"


# ---------------------------------------------------------------------------
# Step 1 — clear MongoDB collection
# ---------------------------------------------------------------------------

async def clear_mongo(collection) -> int:
    result = await collection.delete_many({})
    return result.deleted_count


# ---------------------------------------------------------------------------
# Step 2 — delete all objects under voice_library/ in R2
# ---------------------------------------------------------------------------

async def clear_r2(r2_session, r2_config: dict) -> int:
    endpoint = f"https://{r2_config['account_id']}.r2.cloudflarestorage.com"
    deleted = 0

    async with r2_session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=r2_config["access_key"],
        aws_secret_access_key=r2_config["secret_key"],
    ) as s3:
        paginator = s3.get_paginator("list_objects_v2")
        async for page in paginator.paginate(Bucket=r2_config["bucket"], Prefix="voice_library/"):
            objects = page.get("Contents", [])
            if not objects:
                continue
            delete_payload = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
            await s3.delete_objects(Bucket=r2_config["bucket"], Delete=delete_payload)
            deleted += len(objects)
            for obj in objects:
                print(f"   🗑️  Deleted R2: {obj['Key']}")

    return deleted


# ---------------------------------------------------------------------------
# Step 3 — seed from voice_samples/
# ---------------------------------------------------------------------------

async def seed_voices(manager: VoiceLibraryManager) -> dict:
    if not VOICES_DIR.exists():
        print(f"❌ voice_samples directory not found: {VOICES_DIR}")
        return {"ok": [], "failed": []}

    wav_files = sorted(VOICES_DIR.glob("*.wav"))
    if not wav_files:
        print(f"❌ No .wav files found in {VOICES_DIR}")
        return {"ok": [], "failed": []}

    print(f"   Found {len(wav_files)} file(s)\n")
    results = {"ok": [], "failed": []}

    for wav_path in wav_files:
        filename = wav_path.name
        is_standard = filename in STANDARD_VOICES
        label = "🌟 STANDARD" if is_standard else "🎭 character"
        print(f"--- {filename}  [{label}] ---")

        try:
            with open(wav_path, "rb") as f:
                audio_stream = io.BytesIO(f.read())

            voice_id = await manager.add_voice(
                input_audio=audio_stream,
                filename=filename,
                start_time="00:00",
                is_standard=is_standard,
            )
            print(f"✅ voice_id: {voice_id}\n")
            results["ok"].append((filename, voice_id, is_standard))

        except Exception as e:
            print(f"❌ Failed: {e}\n")
            import traceback
            traceback.print_exc()
            results["failed"].append(filename)

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print("=" * 55)
    print("  SEED STANDARD VOICES")
    print("=" * 55)

    collection, r2_session, r2_config = get_clients()
    manager = VoiceLibraryManager(collection, r2_session, r2_config)

    # Step 1
    print("\n[1/3] Clearing MongoDB voice_library collection...")
    mongo_deleted = await clear_mongo(collection)
    print(f"   Deleted {mongo_deleted} document(s) from MongoDB\n")

    # Step 2
    print("[2/3] Clearing R2 voice_library/ prefix...")
    r2_deleted = await clear_r2(r2_session, r2_config)
    print(f"   Deleted {r2_deleted} object(s) from R2\n")

    # Step 3
    print("[3/3] Seeding voices from tests/voice_samples/...")
    results = await seed_voices(manager)

    # Summary
    print("=" * 55)
    print(f"✅ {len(results['ok'])} voice(s) seeded successfully")
    if results["failed"]:
        print(f"❌ {len(results['failed'])} failed: {results['failed']}")
    print("=" * 55)

    if results["ok"]:
        print("\nFinal voice library:")
        for filename, voice_id, is_standard in results["ok"]:
            marker = "🌟" if is_standard else "  "
            print(f"  {marker} {voice_id}  ←  {filename}")

    print("\nMongo and R2 are now in sync.")


if __name__ == "__main__":
    asyncio.run(main())