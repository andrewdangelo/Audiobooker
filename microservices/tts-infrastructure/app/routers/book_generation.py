"""
Book Generation Router
======================
Receives the trigger from pdf-processor once a script JSON is ready,
kicks off an async generation job, and exposes a status endpoint so
anything (frontend, pdf-processor, backend) can poll progress.

Endpoints:
    POST /start          — trigger generation, returns job_id (202)
    GET  /job/{job_id}   — poll job status
    GET  /jobs           — list all jobs (debug)
"""

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from app.core.config_settings import settings
from app.services.book_generation_service import (
    create_job,
    get_job,
    run_book_generation,
    JOB_PREFIX,
)
from app.core.redis_manager import redis_manager

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def _require_internal_key(x_internal_service_key: Optional[str] = Header(None)) -> None:
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


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    pipeline_stage: Optional[str] = None
    message: str
    total_chunks: Optional[int] = None
    chunks_completed: Optional[int] = None
    chunks_failed: Optional[int] = None
    voice_id: Optional[str] = None
    error: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[dict] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=StartGenerationResponse, status_code=202)
async def start_generation(
    request: StartGenerationRequest,
    background_tasks: BackgroundTasks,
    x_internal_service_key: Optional[str] = Header(None),
):
    """
    Trigger async audio generation for a book.
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
        "message": "Job queued",
        "created_at": datetime.utcnow().isoformat(),
    })

    background_tasks.add_task(
        run_book_generation,
        job_id=job_id,
        book_id=request.book_id,
        script_r2_key=request.script_r2_key,
        user_id=request.user_id,
    )

    logger.info("Book generation job %s queued for book %s", job_id, request.book_id)

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

    import json

    def _int(v, default=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def _parse_result(v):
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return None
        return None

    return JobStatusResponse(
        job_id=str(job.get("job_id", job_id)),
        status=str(job.get("status", "unknown")),
        progress=max(0, min(100, _int(job.get("progress", 0)))),
        pipeline_stage=job.get("pipeline_stage"),
        message=str(job.get("message", "")),
        total_chunks=_int(job.get("total_chunks")) or None,
        chunks_completed=_int(job.get("chunks_completed")) or None,
        chunks_failed=_int(job.get("chunks_failed")) or None,
        voice_id=job.get("voice_id"),
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