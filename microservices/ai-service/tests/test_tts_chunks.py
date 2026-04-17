"""
TTS Chunk Processing — POC Smoke Test
======================================
Processes book quote chunks through the TTS pipeline end-to-end:

  1. Loads chunks from tests/quote_chunks/chunk_tts_poc.json
  2. For each chunk:
       a. Fetches the reference voice WAV from R2
          (at voice_library/processed_voice_clips/{voice_id}.wav)
       b. Calls AISpeechService.generate_speech() → raw WAV bytes
       c. Uploads the generated WAV to R2
          (at audiobook_chunks/{audiobook_id}/{chunk_index}.wav)
  3. Prints a per-chunk result summary.

Run from the project root:
    python -m tests.test_tts_chunks

Before running:
  - Make sure your voice library is seeded (run test_add_voices.py first).
  - Replace "REPLACE_WITH_YOUR_VOICE_ID" in tests/quote_chunks/chunk_tts_poc.json
    with a real voice_id from your Mongo voice_library collection.
"""

import asyncio
import json
import io
from pathlib import Path

import aioboto3

from tests.client_factory import get_clients
from app.services.ai_speech_service import AISpeechService
from app.core.config_settings import settings

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
CHUNKS_PATH = SCRIPT_DIR / "quote_chunks" / "chunk_tts_poc.json"


# ---------------------------------------------------------------------------
# R2 helpers  (async, using aioboto3 — same pattern as VoiceLibraryManager)
# ---------------------------------------------------------------------------

def _r2_client_ctx(r2_session, r2_config: dict):
    """Returns an async context manager for an aioboto3 S3 client."""
    return r2_session.client(
        "s3",
        endpoint_url=f"https://{r2_config['account_id']}.r2.cloudflarestorage.com",
        aws_access_key_id=r2_config["access_key"],
        aws_secret_access_key=r2_config["secret_key"],
    )


async def fetch_voice_bytes(r2_session, r2_config: dict, voice_id: str) -> bytes:
    """
    Download the reference voice clip from R2.
    Path: voice_library/processed_voice_clips/{voice_id}.wav
    """
    key = f"voice_library/processed_voice_clips/{voice_id}.wav"
    async with _r2_client_ctx(r2_session, r2_config) as s3:
        response = await s3.get_object(Bucket=r2_config["bucket"], Key=key)
        return await response["Body"].read()


async def upload_chunk_audio(
    r2_session,
    r2_config: dict,
    audiobook_id: str,
    chunk_index: int,
    audio_bytes: bytes,
) -> str:
    """
    Upload a generated chunk WAV to R2.
    Path: audiobook_chunks/{audiobook_id}/{chunk_index}.wav
    Returns the R2 key.
    """
    key = f"audiobook_chunks/{audiobook_id}/{chunk_index}.wav"
    async with _r2_client_ctx(r2_session, r2_config) as s3:
        await s3.put_object(
            Bucket=r2_config["bucket"],
            Key=key,
            Body=audio_bytes,
            ContentType="audio/wav",
        )
    return key


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

async def process_chunk(r2_session, r2_config: dict, audiobook_id: str, chunk: dict) -> dict:
    """
    Process a single chunk through the full TTS pipeline.
    Returns a result dict with status, key, and size (or error).
    """
    chunk_index = chunk["chunk_index"]
    voice_id = chunk["voice_id"]
    quote = chunk["quote"]
    emotion = chunk.get("emotion", "narrative, calm")
    emotion_strength = chunk.get("emotion_strength", 0.5)

    print(f"\n--- Chunk {chunk_index} ---")
    print(f"   Voice ID : {voice_id}")
    print(f"   Emotion  : {emotion} (strength {emotion_strength})")
    print(f"   Quote    : {quote[:80]}{'...' if len(quote) > 80 else ''}")

    try:
        # Step 1: fetch reference voice bytes from R2
        print(f"   ⬇️  Fetching voice clip from R2...")
        voice_bytes = await fetch_voice_bytes(r2_session, r2_config, voice_id)
        print(f"   ✅ Got {len(voice_bytes):,} bytes")

        # Step 2: generate speech
        print(f"   🎙️  Calling TTS model...")
        audio_bytes = await AISpeechService.generate_speech(
            voice_sample_bytes=voice_bytes,
            quote=quote,
            emotion=emotion,
            emotion_strength=emotion_strength,
        )
        print(f"   ✅ Generated {len(audio_bytes):,} bytes of audio")

        # Step 3: upload to R2
        print(f"   ⬆️  Uploading to R2...")
        r2_key = await upload_chunk_audio(
            r2_session, r2_config, audiobook_id, chunk_index, audio_bytes
        )
        print(f"   ✅ Uploaded → {r2_key}")

        return {
            "chunk_index": chunk_index,
            "status": "ok",
            "r2_key": r2_key,
            "audio_size_bytes": len(audio_bytes),
        }

    except Exception as e:
        import traceback
        print(f"   ❌ Failed: {e}")
        traceback.print_exc()
        return {
            "chunk_index": chunk_index,
            "status": "failed",
            "error": str(e),
        }


async def main():
    # --- Load input data ---
    if not CHUNKS_PATH.exists():
        print(f"❌ Chunks file not found: {CHUNKS_PATH}")
        print("   Create tests/quote_chunks/chunk_tts_poc.json first.")
        return

    with open(CHUNKS_PATH) as f:
        data = json.load(f)

    audiobook_id = data["audiobook_id"]
    chunks = data["chunks"]

    print("=" * 55)
    print("  TTS Chunk Processing — POC Smoke Test")
    print("=" * 55)
    print(f"  Audiobook ID : {audiobook_id}")
    print(f"  Chunks       : {len(chunks)}")
    print("=" * 55)

    # --- Build R2 session (no Mongo needed for this test) ---
    _, r2_session, r2_config = get_clients()

    # --- Process chunks (sequential for POC; trivially parallelisable later) ---
    results = []
    for chunk in chunks:
        result = await process_chunk(r2_session, r2_config, audiobook_id, chunk)
        results.append(result)

    # --- Summary ---
    print("\n" + "=" * 55)
    print("  RESULTS SUMMARY")
    print("=" * 55)
    ok = [r for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] == "failed"]

    for r in ok:
        print(f"  ✅ Chunk {r['chunk_index']:>3}  →  {r['r2_key']}  ({r['audio_size_bytes']:,} bytes)")
    for r in failed:
        print(f"  ❌ Chunk {r['chunk_index']:>3}  →  {r['error']}")

    print(f"\n  {len(ok)}/{len(results)} chunks succeeded.")
    print("=" * 55)


if __name__ == "__main__":
    asyncio.run(main())