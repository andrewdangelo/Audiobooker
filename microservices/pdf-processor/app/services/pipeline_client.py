"""
HTTP helpers for the conversion pipeline: optional AI/TTS health checks, TTS
narration (ADR-001), and backend finalization.
"""
from __future__ import annotations

import io
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config_settings import settings

logger = logging.getLogger(__name__)


async def ping_service_health(url: Optional[str], label: str) -> bool:
    """Best-effort GET; returns True if 2xx or URL skipped."""
    if not url or not url.strip():
        return True
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url.strip().rstrip("/"))
            if r.status_code < 300:
                logger.info("%s health OK (%s)", label, url)
                return True
            logger.warning("%s health non-2xx: %s %s", label, r.status_code, url)
            return False
    except Exception as e:
        logger.warning("%s health ping failed (%s): %s", label, url, e)
        return False


async def refund_conversion_credit(
    user_id: str,
    credit_type: str,
    reason: str,
) -> bool:
    """Call auth-service to refund one conversion credit after pipeline failure."""
    base = (settings.AUTH_SERVICE_BASE_URL or "").strip().rstrip("/")
    if not base:
        logger.error("AUTH_SERVICE_BASE_URL not configured; cannot refund credit")
        return False
    url = f"{base}/accounts/credits/refund-conversion"
    payload = {"user_id": user_id, "credit_type": credit_type, "reason": reason}
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            logger.info("Refunded 1 %s credit for user %s", credit_type, user_id)
            return True
    except Exception as e:
        logger.error("Credit refund failed for user %s: %s", user_id, e, exc_info=True)
        return False


async def notify_backend_conversion_complete(
    *,
    user_id: str,
    processor_job_id: str,
    title: str,
    author: str,
    description: Optional[str],
    credit_type: str,
    source_format: str,
    source_r2_path: str,
    processed_text_r2_key: Optional[str],
    script_r2_key: Optional[str],
    chapters: Optional[List[Dict[str, Any]]] = None,
) -> Optional[str]:
    """
    Create backend library book + user_library entry via internal API.
    Returns backend book_id (UUID) or None on failure.
    """
    base = (settings.BACKEND_SERVICE_BASE_URL or "").strip().rstrip("/")
    if not base:
        logger.error("BACKEND_SERVICE_BASE_URL is not configured; skipping backend sync")
        return None

    url = f"{base}/internal/conversion/complete"
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "processor_job_id": processor_job_id,
        "title": title,
        "author": author,
        "description": description,
        "credit_type": credit_type,
        "source_format": source_format,
        "source_r2_path": source_r2_path,
        "processed_text_r2_key": processed_text_r2_key,
        "script_r2_key": script_r2_key,
    }
    if chapters:
        payload["chapters"] = chapters
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            book_id = data.get("book_id")
            if book_id:
                return str(book_id)
            logger.error("Backend conversion response missing book_id: %s", data)
            return None
    except Exception as e:
        logger.error("Backend conversion notify failed: %s", e, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Script-to-TTS adapter (multivoice chapter-based)
# ---------------------------------------------------------------------------


def script_to_tts_batches(
    script: Dict[str, Any],
    voice_map: Dict[str, str],
    default_voice_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a chapter-based script.json into per-chapter TTS batch request payloads.

    voice_map maps canonical speaker names to TTS voice IDs, e.g.:
        {"Narrator": "EXAVITQu4vr4xnSDxMaL", "John": "pNInz6obpgDQGcFmaJgB"}

    Returns a list of chapter batches, each batch is a dict:
        {
            "chapter_id": int,
            "chapter_title": str,
            "chunks": [{"chunk_id": str, "text": str, "voice_id": str, "speaker": str}, ...]
        }
    """
    chapters = script.get("chapters", [])
    fallback_voice = default_voice_id or next(iter(voice_map.values()), None)
    batches: List[Dict[str, Any]] = []
    global_seg_id = 0

    for chapter in chapters:
        chapter_chunks: List[Dict[str, Any]] = []
        for seg in chapter.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:
                continue
            speaker = seg.get("speaker", "Narrator")
            voice_id = voice_map.get(speaker) or voice_map.get("Narrator") or fallback_voice
            chapter_chunks.append({
                "chunk_id": str(global_seg_id),
                "text": text,
                "voice_id": voice_id,
                "speaker": speaker,
            })
            global_seg_id += 1

        if chapter_chunks:
            batches.append({
                "chapter_id": chapter.get("chapter_id", 0),
                "chapter_title": chapter.get("title", ""),
                "chunks": chapter_chunks,
            })

    logger.info(
        "Built %d TTS chapter batches (%d total segments) from script",
        len(batches), global_seg_id,
    )
    return batches


# ---------------------------------------------------------------------------
# TTS narration helpers (ADR-001: pdf-processor orchestrates)
# ---------------------------------------------------------------------------


async def _call_tts_batch(
    chunks: List[Dict[str, Any]],
    voice_id: str,
    provider: str,
) -> List[Dict[str, Any]]:
    """POST to TTS service /batch and return the per-chunk result list."""
    base = settings.TTS_SERVICE_BASE_URL.rstrip("/")
    url = f"{base}/batch"

    payload = {
        "json_data": chunks,
        "provider": provider,
        "voice_id": voice_id,
    }
    async with httpx.AsyncClient(timeout=600.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return data.get("results", [])


async def _download_tts_audio(chunk_id: str) -> bytes:
    """GET audio bytes from the TTS service for a completed chunk."""
    base = settings.TTS_SERVICE_BASE_URL.rstrip("/")
    url = f"{base}/audio/{chunk_id}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


async def _patch_book_audio(
    book_id: str,
    audio_url: Optional[str] = None,
    duration: Optional[float] = None,
    narration_status: str = "ready",
) -> bool:
    """PATCH /internal/books/{book_id}/audio on the backend."""
    base = (settings.BACKEND_SERVICE_BASE_URL or "").strip().rstrip("/")
    if not base:
        logger.error("BACKEND_SERVICE_BASE_URL not configured; cannot patch audio")
        return False

    url = f"{base}/internal/books/{book_id}/audio"
    payload: Dict[str, Any] = {"narration_status": narration_status}
    if audio_url:
        payload["audio_url"] = audio_url
    if duration is not None:
        payload["duration"] = duration
    headers = {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.patch(url, json=payload, headers=headers)
            r.raise_for_status()
            logger.info("Book %s audio patched: %s", book_id, narration_status)
            return True
    except Exception as e:
        logger.error("patch_book_audio failed for %s: %s", book_id, e, exc_info=True)
        return False


async def generate_and_persist_narration(
    *,
    book_id: str,
    processed_text_r2_key: str,
    voice_id: Optional[str] = None,
    provider: Optional[str] = None,
    progress_cb: Optional[Any] = None,
) -> Tuple[bool, Optional[str]]:
    """
    End-to-end single-voice narration:
    1. Download processed text JSON from R2
    2. Build chunk list for TTS batch
    3. Call TTS /batch
    4. Download and concatenate audio files
    5. Upload merged MP3 to R2
    6. PATCH backend book with audio_url + duration

    Returns (success, audio_r2_key | None).
    """
    from app.services.r2_service import R2Service

    r2 = R2Service()
    effective_voice = voice_id or settings.DEFAULT_BASIC_VOICE_ID
    effective_provider = provider or settings.TTS_PROVIDER

    # 1. Download processed text
    try:
        raw = r2.download_file(processed_text_r2_key)
        processed = json.loads(raw)
    except Exception as e:
        logger.error("Failed to download processed text %s: %s", processed_text_r2_key, e)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    chunks_raw = processed.get("chunks", [])
    if not chunks_raw:
        logger.warning("No chunks in processed text for book %s", book_id)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    # 2. Build TTS input — each chunk needs chunk_id and text
    tts_chunks: List[Dict[str, Any]] = []
    for i, chunk in enumerate(chunks_raw):
        text = chunk.get("text", "") if isinstance(chunk, dict) else str(chunk)
        text = text.strip()
        if not text:
            continue
        tts_chunks.append({
            "chunk_id": str(i),
            "text": text,
        })

    if not tts_chunks:
        logger.warning("All chunks empty for book %s", book_id)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    logger.info("Starting TTS for book %s: %d chunks, voice=%s, provider=%s",
                book_id, len(tts_chunks), effective_voice, effective_provider)

    # 3. Call TTS batch
    try:
        results = await _call_tts_batch(tts_chunks, effective_voice, effective_provider)
    except Exception as e:
        logger.error("TTS batch call failed for book %s: %s", book_id, e, exc_info=True)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    successful = [r for r in results if r.get("status") == "success"]
    if not successful:
        logger.error("TTS batch returned 0 successful chunks for book %s", book_id)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    # 4. Download audio for each successful chunk and concatenate
    audio_parts: List[bytes] = []
    total_duration = 0.0
    for r in sorted(successful, key=lambda x: int(x.get("chunk_id", 0))):
        try:
            audio_bytes = await _download_tts_audio(r["chunk_id"])
            audio_parts.append(audio_bytes)
            total_duration += r.get("duration_seconds", 0) or 0
        except Exception as e:
            logger.warning("Failed to download chunk %s audio: %s", r["chunk_id"], e)

    if not audio_parts:
        logger.error("No audio parts downloaded for book %s", book_id)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    merged = b"".join(audio_parts)
    logger.info("Merged %d audio parts (%.1f MB, ~%.0fs) for book %s",
                len(audio_parts), len(merged) / (1024 * 1024), total_duration, book_id)

    # 5. Upload to R2
    audio_r2_key = f"narration_audio/{book_id}/{uuid.uuid4().hex}.mp3"
    try:
        r2.upload_processed_data(
            key=audio_r2_key,
            data=merged,
            content_type="audio/mpeg",
        )
    except Exception as e:
        logger.error("R2 upload failed for narration %s: %s", audio_r2_key, e, exc_info=True)
        await _patch_book_audio(book_id, None, None, "failed")
        return False, None

    # Build the public/signed URL that playback.py will serve
    audio_url = f"https://{settings.R2_BUCKET_NAME}.r2.cloudflarestorage.com/{audio_r2_key}"

    # 6. PATCH backend book
    ok = await _patch_book_audio(book_id, audio_url, total_duration, "ready")
    if not ok:
        return False, audio_r2_key

    logger.info("Narration complete for book %s → %s", book_id, audio_r2_key)
    return True, audio_r2_key
