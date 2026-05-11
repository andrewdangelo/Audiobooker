"""
Book Generation Router
======================
Receives the trigger from pdf-processor once a script JSON is ready,
enqueues an ARQ job, and exposes a status endpoint so anything
(frontend, pdf-processor, backend) can poll progress.

Endpoints:
    POST /start          — enqueue generation job, returns job_id (202)
    GET  /job/{job_id}   — poll job status
    GET  /jobs           — list all jobs (debug)
"""

import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel

from app.core.config_settings import settings
from app.services.book_generation_service import (
    create_job,
    get_job,
    JOB_PREFIX,
)
from app.core.redis_manager import redis_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def _require_internal_key(x_internal_service_key: Optional[str]) -> None:
    if x_internal_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: invalid internal service key")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class StartGenerationRequest(BaseModel):
    book_id: str
    script_r2_key: str
    user_id: str


class StartGenerationResponse(BaseModel):
    job_id: str
    status: str
    message: str


class ChunkResult(BaseModel):
    succeeded: List[str]        # R2 keys of successfully generated chunks
    failed: List[int]           # indices of chunks that errored during TTS
    skipped: List[int]          # indices of chunks with empty text (no audio needed)


class GenerationResult(BaseModel):
    book_id: str
    total_chunks: int
    chunks: ChunkResult
    assignment_map: Dict[str, str]
    voice_ids: List[str]


class JobStatusResponse(BaseModel):
    job_id: str
    status: str                          # pending | processing | completed | failed
    progress: int                        # 0-100 — use this for the progress bar
    pipeline_stage: Optional[str] = None # human-readable current stage
    message: str
    # Live counters — updated every 2s during tts_generation stage
    # These are for real-time polling display only.
    # On completion, read authoritative values from result.chunks instead.
    chunks_completed: Optional[int] = None
    chunks_failed: Optional[int] = None
    chunks_skipped: Optional[int] = None
    voice_ids: Optional[List[str]] = None
    error: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[GenerationResult] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _int_or_none(v) -> Optional[int]:
    """
    Returns int if value exists and is parseable, None if genuinely absent.
    Does NOT coerce 0 to None — 0 is a valid meaningful value.
    """
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _parse_json_field(v):
    """Parse a Redis field that was stored as a JSON string."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    try:
        return json.loads(v)
    except Exception:
        return None


def _parse_result(v) -> Optional[GenerationResult]:
    """Parse the result field into a typed GenerationResult."""
    raw = _parse_json_field(v)
    if not raw:
        return None
    try:
        return GenerationResult(
            book_id=raw["book_id"],
            total_chunks=raw["total_chunks"],
            chunks=ChunkResult(**raw["chunks"]),
            assignment_map=raw["assignment_map"],
            voice_ids=raw["voice_ids"],
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=StartGenerationResponse, status_code=202)
async def start_generation(
    request: StartGenerationRequest,
    req: Request,
    x_internal_service_key: Optional[str] = Header(None),
):
    """
    Enqueue an audio generation job for a book.
    Called by pdf-processor after the script JSON is ready in R2.
    Returns 202 immediately with a job_id to poll.
    """
    _require_internal_key(x_internal_service_key)

    job_id = str(uuid.uuid4())

    await create_job(job_id, {
        "job_id": job_id,
        "book_id": request.book_id,
        "user_id": request.user_id,
        "script_r2_key": request.script_r2_key,
        "status": "pending",
        "pipeline_stage": "pending",
        "progress": 0,
        "message": "Job queued — waiting for worker",
        "created_at": datetime.utcnow().isoformat(),
    })

    arq_pool = req.app.state.arq_pool
    await arq_pool.enqueue_job(
        "run_book_generation",
        job_id=job_id,
        book_id=request.book_id,
        script_r2_key=request.script_r2_key,
        user_id=request.user_id,
    )

    logger.info("Book generation job %s enqueued for book %s", job_id, request.book_id)

    return StartGenerationResponse(
        job_id=job_id,
        status="accepted",
        message="Audio generation job queued",
    )


@router.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll the status of a generation job."""
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatusResponse(
        job_id=str(job.get("job_id", job_id)),
        status=str(job.get("status", "unknown")),
        progress=max(0, min(100, _int_or_none(job.get("progress")) or 0)),
        pipeline_stage=job.get("pipeline_stage"),
        message=str(job.get("message", "")),
        chunks_completed=_int_or_none(job.get("chunks_completed")),
        chunks_failed=_int_or_none(job.get("chunks_failed")),
        chunks_skipped=_int_or_none(job.get("chunks_skipped")),
        voice_ids=_parse_json_field(job.get("voice_ids")),
        error=job.get("error"),
        completed_at=job.get("completed_at"),
        result=_parse_result(job.get("result")),
    )


@router.get("/jobs")
async def list_jobs():
    """List all book generation jobs (debug/admin)."""
    pattern = f"{JOB_PREFIX}:*"
    keys = await redis_manager.keys(pattern)
    jobs = []
    for key in keys:
        jid = key.replace(f"{JOB_PREFIX}:", "")
        job = await get_job(jid)
        if job:
            jobs.append(job)
    return {"total": len(jobs), "jobs": jobs}