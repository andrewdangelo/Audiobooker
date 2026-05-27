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

import asyncio
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

# Max concurrent TTS calls to ai-service at any one time.
# Tune this against your HF endpoint's capacity.
# 5 is a safe starting point — increase if the endpoint handles it without
# rate limiting, decrease if you see 429s or OOM errors on the HF side.
TTS_CONCURRENCY = 5


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

        assignment_map = {char["name"]: voice_id for char in characters}
        logger.info("Voice assignment: %d characters → voice_id=%s", len(characters), voice_id)
        return assignment_map

    except Exception as e:
        logger.error("Voice assignment failed: %s", e)
        raise


async def _warmup_tts() -> None:
    """
    Tell ai-service to initialize and wake up the TTS model before
    the generation loop starts. Blocks until the model is ready.
    Called once per job — ensures no chunk task races on initialization.
    """
    url = f"{settings.AI_SERVICE_BASE_URL.rstrip('/')}/internal/tts/warmup"
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}
    async with httpx.AsyncClient(timeout=400.0) as client:
        resp = await client.post(url, headers=headers)
        resp.raise_for_status()
    logger.info("TTS model warmed up and ready")


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
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content


# ---------------------------------------------------------------------------
# Concurrent chunk processor
# ---------------------------------------------------------------------------

async def _process_chunk(
    *,
    idx: int,
    line: Dict,
    session: aioboto3.Session,
    voice_cache: Dict[str, bytes],
    assignment_map: Dict[str, str],
    fallback_voice_id: str,
    book_id: str,
    job_id: str,
    semaphore: asyncio.Semaphore,
    # Shared mutable state — written by index so no races between tasks
    succeeded: List[Optional[str]],   # succeeded[idx] = R2 key or None
    failed: List[Optional[int]],      # failed[idx] = idx or None
    skipped: List[Optional[int]],     # skipped[idx] = idx or None
    counter: Dict[str, int],
) -> None:
    """
    Process a single script line: call TTS, upload chunk WAV to R2.
    Acquires the semaphore before doing any work — at most TTS_CONCURRENCY
    of these run simultaneously across the whole job.

    Results written into pre-allocated lists by index — no ordering races.
    Counter updates are safe without locks (asyncio is single-threaded).
    """
    text = line.get("text", "").strip()
    speaker = line.get("speaker", "")

    # Empty lines are skipped — not a failure, just no audio needed
    if not text:
        logger.debug("Job %s: skipping empty line %d", job_id, idx)
        skipped[idx] = idx
        counter["skipped"] += 1
        return

    voice_id = assignment_map.get(speaker)
    if voice_id is None:
        logger.warning(
            "Job %s: unknown speaker '%s' at line %d — using fallback voice",
            job_id, speaker, idx,
        )
        voice_id = fallback_voice_id

    voice_bytes = voice_cache[voice_id]
    emotion = line.get("emotion", DEFAULT_EMOTION)
    emotion_strength = float(line.get("emotion_strength", DEFAULT_EMOTION_STRENGTH))

    async with semaphore:
        try:
            audio_bytes = await _call_tts(voice_bytes, text, emotion, emotion_strength)
            chunk_key = f"audiobook_chunks/{book_id}/{idx}.wav"
            await _r2_upload(session, chunk_key, audio_bytes)
            succeeded[idx] = chunk_key
            counter["completed"] += 1
            logger.debug("Job %s: chunk %d done (%s)", job_id, idx, speaker)

        except Exception as e:
            logger.error("Job %s chunk %d (speaker=%s) failed: %s", job_id, idx, speaker, e)
            failed[idx] = idx
            counter["failed"] += 1


# ---------------------------------------------------------------------------
# Progress reporter
# ---------------------------------------------------------------------------

async def _report_progress(
    job_id: str,
    counter: Dict[str, int],
    total: int,
    stop_event: asyncio.Event,
) -> None:
    """
    Runs concurrently with the chunk tasks via asyncio.create_task.
    Wakes up every 2 seconds and writes current progress to Redis.
    Exits cleanly when stop_event is set after all chunk tasks finish.
    """
    while not stop_event.is_set():
        done = counter["completed"] + counter["failed"] + counter["skipped"]
        progress = 20 + int(done / total * 75) if total > 0 else 20
        await update_job(job_id, {
            "pipeline_stage": "tts_generation",
            "progress": progress,
            "chunks_completed": counter["completed"],
            "chunks_failed": counter["failed"],
            "chunks_skipped": counter["skipped"],
            "message": f"Generating audio: {done}/{total} chunks",
        })
        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Main background task
# ---------------------------------------------------------------------------

async def run_book_generation(
    ctx: dict,
    job_id: str,
    book_id: str,
    script_r2_key: str,
    user_id: str,
) -> None:
    """
    Full generation loop. Called by ARQ worker.

    Steps:
        1. Download script JSON from R2
        2. Voice assignment — ONCE against characters list
               → assignment_map: {character_name: voice_id}
        3. Build voice_cache — download each unique voice WAV once
               → voice_cache: {voice_id: bytes}
        3.5 Warm up TTS model — blocks until HF endpoint is ready
        4. Concurrent TTS loop
               - Semaphore caps concurrent HF calls at TTS_CONCURRENCY
               - reporter task runs independently via create_task
               - succeeded/failed/skipped tracked by index
        5. Guard — all chunks failed → job failed
        6. Mark completed with final chunk schema
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
        await update_job(job_id, {
            "pipeline_stage": "voice_assignment",
            "progress": 10,
            "message": f"Assigning voices to {len(characters)} characters",
        })

        assignment_map: Dict[str, str] = await _assign_voices(characters)
        unique_voice_ids = set(assignment_map.values())

        await update_job(job_id, {
            "assignment_map": json.dumps(assignment_map),
            "total_chunks": total,
            "voice_ids": json.dumps(list(unique_voice_ids)),
            "message": f"Voices assigned to {len(assignment_map)} characters",
        })

        # ── Step 3: build voice_cache — download each unique WAV once ────
        await update_job(job_id, {
            "pipeline_stage": "downloading_voices",
            "progress": 15,
            "message": f"Downloading {len(unique_voice_ids)} unique voice sample(s)",
        })

        voice_cache: Dict[str, bytes] = {}
        for voice_id in unique_voice_ids:
            voice_cache[voice_id] = await _r2_download(session, f"voice_library/{voice_id}.wav")
            logger.info("Job %s: cached voice_id=%s (%d bytes)", job_id, voice_id, len(voice_cache[voice_id]))

        # ── Step 3.5: warm up TTS model before loop ──────────────────────
        # Blocks here until HF endpoint is running and client is initialized.
        # Prevents all concurrent chunk tasks from racing on initialization.
        await update_job(job_id, {
            "pipeline_stage": "warming_up_model",
            "progress": 18,
            "message": "Warming up TTS model — may take a minute if scaled to zero",
        })

        await _warmup_tts()

        # ── Step 4: concurrent TTS loop ──────────────────────────────────
        # Pre-allocated by index — each task writes only its own slot.
        succeeded: List[Optional[str]] = [None] * total   # R2 keys
        failed: List[Optional[int]] = [None] * total      # chunk indices
        skipped: List[Optional[int]] = [None] * total     # chunk indices
        counter: Dict[str, int] = {"completed": 0, "failed": 0, "skipped": 0}
        semaphore = asyncio.Semaphore(TTS_CONCURRENCY)
        stop_event = asyncio.Event()
        fallback_voice_id = next(iter(assignment_map.values()))

        chunk_tasks = [
            _process_chunk(
                idx=idx,
                line=line,
                session=session,
                voice_cache=voice_cache,
                assignment_map=assignment_map,
                fallback_voice_id=fallback_voice_id,
                book_id=book_id,
                job_id=job_id,
                semaphore=semaphore,
                succeeded=succeeded,
                failed=failed,
                skipped=skipped,
                counter=counter,
            )
            for idx, line in enumerate(lines)
        ]

        # Reporter runs independently — not inside gather so it doesn't block completion
        reporter = asyncio.create_task(
            _report_progress(job_id, counter, total, stop_event)
        )

        await asyncio.gather(*chunk_tasks)
        stop_event.set()
        await reporter

        # ── Step 5: guard — all chunks failed means job failed ───────────
        if counter["completed"] == 0:
            raise ValueError(f"All {total} chunks failed — no audio generated")

        # ── Step 6: complete ─────────────────────────────────────────────
        result = {
            "book_id": book_id,
            "total_chunks": total,
            "chunks": {
                "succeeded": [k for k in succeeded if k is not None],
                "failed": [i for i in failed if i is not None],
                "skipped": [i for i in skipped if i is not None],
            },
            "assignment_map": assignment_map,
            "voice_ids": list(unique_voice_ids),
        }

        await update_job(job_id, {
            "status": "completed",
            "pipeline_stage": "completed",
            "progress": 100,
            # Final authoritative counts — written atomically here, not from reporter
            "chunks_completed": counter["completed"],
            "chunks_failed": counter["failed"],
            "chunks_skipped": counter["skipped"],
            "message": f"Audio generation complete: {counter['completed']}/{total} chunks",
            "completed_at": datetime.utcnow().isoformat(),
            "result": json.dumps(result),
        })

        logger.info(
            "Job %s complete — %d/%d chunks OK, %d failed, %d skipped",
            job_id, counter["completed"], total, counter["failed"], counter["skipped"],
        )

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