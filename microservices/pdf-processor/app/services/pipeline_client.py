"""
HTTP helpers for the conversion pipeline: optional AI/TTS health checks and backend finalization.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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
