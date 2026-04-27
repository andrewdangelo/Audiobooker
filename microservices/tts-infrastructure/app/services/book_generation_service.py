"""
BookGenerationService
=====================
Owns the async job loop that converts a processed script JSON (from R2) into
per-chunk WAV files (written back to R2) using ai-service for TTS inference.

Job lifecycle (tracked in Redis hashes):
    pending → processing → completed | failed

Progress is reported as 0-100 so the frontend can poll the same way it
polls pdf-processor jobs.

Redis key: book_gen_job:{job_id}
R2 output:  audiobook_chunks/{book_id}/{chunk_index}.wav
"""

import base64
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import aioboto3
import httpx

from app.core.config_settings import settings
from app.core.redis_manager import redis_manager

logger = logging.getLogger(__name__)

JOB_PREFIX = "book_gen_job"
JOB_TTL = 60 * 60 * 48  # 48 hours

DEFAULT_EMOTION = "narrative, calm"
DEFAULT_EMOTION_STRENGTH = 0.5


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

async def create_job(job_id: str, fields: Dict[str, Any]) -> None:
    key = f"{JOB_PREFIX}:{job_id}"
    for field, value in fields.items():
        if not isinstance(value, str):
            value = json.dumps(value)
        await redis_manager.hset(key, field, value)
    await redis_manager.expire(key, JOB_TTL)


async def update_job(job_id: str, updates: Dict[str, Any]) -> None:
    key = f"{JOB_PREFIX}:{job_id}"
    for field, value in updates.items():
        if not isinstance(value, str):
            value = json.dumps(value)
        await redis_manager.hset(key, field, value)
    await redis_manager.expire(key, JOB_TTL)


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    key = f"{JOB_PREFIX}:{job_id}"
    data = await redis_manager.hgetall(key)
    return data if data else None


# ---------------------------------------------------------------------------
# R2 helpers
# ---------------------------------------------------------------------------

def _r2_client(session: aioboto3.Session):
    endpoint = settings.R2_ENDPOINT_URL or f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    return session.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    )


async def _r2_download(session: aioboto3.Session, key: str) -> bytes:
    async with _r2_client(session) as s3:
        resp = await s3.get_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
        return await resp["Body"].read()


async def _r2_upload(session: aioboto3.Session, key: str, data: bytes, content_type: str = "audio/wav") -> None:
    async with _r2_client(session) as s3:
        await s3.put_object(
            Bucket=settings.R2_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )


# ---------------------------------------------------------------------------
# ai-service clients
# ---------------------------------------------------------------------------

async def _assign_voices(characters: List[Dict]) -> Dict[str, str]:
    """
    Call ai-service once with the full characters list to get a stable
    {character_name: voice_id} assignment map for the whole book.

    Phase 1 (quick=True): ai-service picks one random standard voice and
    maps every character name to it. Consistent — same voice_id for every
    speaker for the duration of this book.

    Phase 2 (later): pass quick=False and characters to assign_voice_multiple
    for a full cast with per-character voice matching.
    """
    url = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/voice-library/assign-single"
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"quick": True}, headers=headers)
            resp.raise_for_status()
            voice_id = resp.json().get("voice_id")

        if not voice_id:
            raise ValueError("ai-service returned no voice_id")

        # Map every character name to the same narrator voice_id
        assignment_map = {char["name"]: voice_id for char in characters}
        logger.info("Voice assignment: %d characters → voice_id=%s", len(characters), voice_id)
        return assignment_map

    except Exception as e:
        logger.error("Voice assignment failed: %s", e)
        raise


async def _call_tts(voice_bytes: bytes, text: str, emotion: str, emotion_strength: float) -> bytes:
    """
    POST to ai-service internal TTS endpoint.
    voice_bytes: WAV bytes of the reference clip, already downloaded from R2.
    Returns raw WAV bytes of the generated audio.
    """
    url = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/tts/generate-chunk"
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}
    payload = {
        "voice_sample_b64": base64.b64encode(voice_bytes).decode(),
        "text": text,
        "emotion": emotion,
        "emotion_strength": emotion_strength,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# Main background task
# ---------------------------------------------------------------------------

async def run_book_generation(
    job_id: str,
    book_id: str,
    script_r2_key: str,
    user_id: str,
) -> None:
    """
    Full generation loop. Runs as a FastAPI BackgroundTask.

    Steps:
        1. Download script JSON from R2
        2. Voice assignment — called ONCE with script["characters"]
               Returns assignment_map: {character_name: voice_id}
        3. Build voice_cache — download each unique voice WAV once
               voice_cache: {voice_id: bytes}
        4. TTS loop over script lines
               For each line:
                 - look up speaker in assignment_map → voice_id
                 - look up voice_id in voice_cache → voice_bytes
                 - read emotion/emotion_strength from line (defaults if absent)
                 - call ai-service TTS, upload WAV chunk to R2
        5. Mark job completed (or failed)
    """
    session = aioboto3.Session()

    try:
        # ── Step 1: download script ──────────────────────────────────────
        await update_job(job_id, {
            "status": "processing",
            "pipeline_stage": "downloading_script",
            "progress": 5,
            "message": "Downloading script from R2",
        })

        script_bytes = await _r2_download(session, script_r2_key)
        script = json.loads(script_bytes)

        lines: List[Dict] = script.get("script", [])
        characters: List[Dict] = script.get("characters", [])
        total = len(lines)

        if total == 0:
            raise ValueError("Script contains 0 lines — nothing to generate")
        if not characters:
            raise ValueError("Script contains no characters list — cannot assign voices")

        logger.info("Job %s: %d lines, %d characters, book %s", job_id, total, len(characters), book_id)

        # ── Step 2: voice assignment (book-level, runs once) ─────────────
        # assignment_map: {character_name: voice_id}
        # Settled here against the full characters list — never touched again.
        await update_job(job_id, {
            "pipeline_stage": "voice_assignment",
            "progress": 10,
            "message": f"Assigning voices to {len(characters)} characters",
        })

        assignment_map: Dict[str, str] = await _assign_voices(characters)

        await update_job(job_id, {
            "assignment_map": json.dumps(assignment_map),
            "message": f"Voices assigned to {len(assignment_map)} characters",
        })

        # ── Step 3: build voice_cache — download each unique WAV once ────
        # voice_cache: {voice_id: bytes}
        await update_job(job_id, {
            "pipeline_stage": "downloading_voices",
            "progress": 15,
            "message": "Downloading voice samples",
        })

        unique_voice_ids = set(assignment_map.values())
        voice_cache: Dict[str, bytes] = {}

        for voice_id in unique_voice_ids:
            voice_cache[voice_id] = await _r2_download(session, f"voice_library/{voice_id}.wav")
            logger.info("Job %s: cached voice_id=%s (%d bytes)", job_id, voice_id, len(voice_cache[voice_id]))

        # ── Step 4: TTS loop ─────────────────────────────────────────────
        completed_chunks = 0
        failed_chunks = 0
        chunk_r2_keys: List[Optional[str]] = []

        # Fallback voice_id in case a speaker name isn't in assignment_map.
        # Shouldn't happen if the LLM chunker and voice assignment are consistent,
        # but guards against edge cases like "Chapter" markers.
        fallback_voice_id = next(iter(assignment_map.values()))

        for idx, line in enumerate(lines):
            text = line.get("text", "").strip()
            speaker = line.get("speaker", "")

            if not text:
                logger.debug("Job %s: skipping empty line %d", job_id, idx)
                chunk_r2_keys.append(None)
                continue

            voice_id = assignment_map.get(speaker, fallback_voice_id)
            voice_bytes = voice_cache[voice_id]
            emotion = line.get("emotion", DEFAULT_EMOTION)
            emotion_strength = float(line.get("emotion_strength", DEFAULT_EMOTION_STRENGTH))

            try:
                audio_bytes = await _call_tts(voice_bytes, text, emotion, emotion_strength)
                chunk_key = f"audiobook_chunks/{book_id}/{idx}.wav"
                await _r2_upload(session, chunk_key, audio_bytes)
                chunk_r2_keys.append(chunk_key)
                completed_chunks += 1

            except Exception as e:
                logger.error("Job %s chunk %d (speaker=%s) failed: %s", job_id, idx, speaker, e)
                chunk_r2_keys.append(None)
                failed_chunks += 1

            # Progress: 15% → 95% across the TTS loop
            progress = 15 + int((idx + 1) / total * 80)
            await update_job(job_id, {
                "pipeline_stage": "tts_generation",
                "progress": progress,
                "chunks_completed": completed_chunks,
                "chunks_failed": failed_chunks,
                "message": f"Generating audio: {idx + 1}/{total} chunks",
            })

        # ── Step 5: complete ─────────────────────────────────────────────
        result = {
            "book_id": book_id,
            "total_chunks": total,
            "chunks_completed": completed_chunks,
            "chunks_failed": failed_chunks,
            "chunk_r2_keys": [k for k in chunk_r2_keys if k],
            "assignment_map": assignment_map,
        }

        await update_job(job_id, {
            "status": "completed",
            "pipeline_stage": "completed",
            "progress": 100,
            "message": f"Audio generation complete: {completed_chunks}/{total} chunks",
            "completed_at": datetime.utcnow().isoformat(),
            "result": json.dumps(result),
        })

        logger.info("Job %s complete — %d/%d chunks OK, %d failed", job_id, completed_chunks, total, failed_chunks)

    except Exception as e:
        logger.error("Job %s fatal error: %s", job_id, e, exc_info=True)
        await update_job(job_id, {
            "status": "failed",
            "pipeline_stage": "failed",
            "progress": 0,
            "message": "Generation failed",
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat(),
        })