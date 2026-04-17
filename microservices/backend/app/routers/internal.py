"""
Internal Router - Service-to-Service Only

Endpoints called by other microservices (e.g. payment-service) to read/write
backend data without direct database access.

All endpoints require the X-Internal-Service-Key header to match the shared
INTERNAL_SERVICE_KEY setting, preventing public access.
"""

import logging
import uuid
from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from app.core.config_settings import settings
from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Security dependency
# ---------------------------------------------------------------------------

def require_internal_key(x_internal_service_key: Optional[str] = Header(None)):
    """Reject requests that don't carry the shared internal service key."""
    if not settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=500, detail="Internal service key not configured")
    if x_internal_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: invalid internal service key")


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class LibraryEntryCreate(BaseModel):
    """Payload for adding a book to a user's library."""
    book_id: str
    progress: float = 0.0
    last_played_at: Optional[datetime] = None
    added_at: Optional[datetime] = None
    completed: bool = False
    order_id: Optional[str] = None


class ConversionCompleteRequest(BaseModel):
    """Called by pdf-processor when extraction (+ optional AI/TTS prep) is done."""

    user_id: str
    processor_job_id: str
    title: str = Field(..., min_length=1)
    author: str = "Unknown"
    description: Optional[str] = None
    credit_type: Literal["basic", "premium"] = "basic"
    source_format: Literal["pdf", "epub"] = "pdf"
    source_r2_path: Optional[str] = None
    processed_text_r2_key: Optional[str] = None
    script_r2_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/library/{user_id}/{book_id}", tags=["Internal"])
async def get_library_entry(
    user_id: str,
    book_id: str,
    _: None = Depends(require_internal_key),
    db=Depends(get_db()),
):
    """Check whether a book is already in a user's library. Returns the entry or 404."""
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    entry = library_service.find_one({"user_id": user_id, "book_id": book_id})
    if not entry:
        raise HTTPException(status_code=404, detail="Library entry not found")
    entry["_id"] = str(entry["_id"])
    return entry


@router.post("/library/{user_id}", status_code=201, tags=["Internal"])
async def add_library_entry(
    user_id: str,
    body: LibraryEntryCreate,
    _: None = Depends(require_internal_key),
    db=Depends(get_db()),
):
    """Add a book to the user's library. Idempotent – skips duplicates."""
    library_service = MongoDBService(db, Collections.USER_LIBRARY)

    existing = library_service.find_one({"user_id": user_id, "book_id": body.book_id})
    if existing:
        existing["_id"] = str(existing["_id"])
        return {"created": False, "entry": existing}

    entry_data = {
        "user_id": user_id,
        "book_id": body.book_id,
        "progress": body.progress,
        "last_played_at": body.last_played_at,
        "added_at": body.added_at or datetime.utcnow(),
        "completed": body.completed,
        "order_id": body.order_id,
    }
    created = library_service.create(entry_data)
    created["_id"] = str(created["_id"])
    return {"created": True, "entry": created}


@router.post("/conversion/complete", status_code=201, tags=["Internal"])
async def complete_conversion_pipeline(
    body: ConversionCompleteRequest,
    _: None = Depends(require_internal_key),
    db=Depends(get_db()),
):
    """
    Create a user-owned audiobook in `books` and link it in `user_library`.
    Idempotent per (user_id, processor_job_id): returns existing book_id if already created.
    """
    book_service = MongoDBService(db, Collections.BOOKS)
    library_service = MongoDBService(db, Collections.USER_LIBRARY)

    existing_book = book_service.find_one({"conversion_job_id": body.processor_job_id})
    if existing_book:
        bid = str(existing_book.get("id") or existing_book.get("_id"))
        lib = library_service.find_one({"user_id": body.user_id, "book_id": bid})
        if not lib:
            library_service.create(
                {
                    "user_id": body.user_id,
                    "book_id": bid,
                    "progress": 0.0,
                    "purchase_type": "premium" if body.credit_type == "premium" else "basic",
                }
            )
        return {"book_id": bid, "processor_job_id": body.processor_job_id, "created": False}

    book_id = str(uuid.uuid4())
    purchase_type = "premium" if body.credit_type == "premium" else "basic"

    book_data = {
        "id": book_id,
        "title": body.title,
        "author": body.author,
        "description": body.description,
        "duration": 0,
        "is_store_item": False,
        "chapters": [],
        "audio_url": None,
        "is_premium": body.credit_type == "premium",
        "conversion_job_id": body.processor_job_id,
        "source_format": body.source_format,
        "source_r2_path": body.source_r2_path,
        "processed_text_r2_key": body.processed_text_r2_key,
        "script_r2_key": body.script_r2_key,
    }
    book_service.create(book_data)

    library_service.create(
        {
            "user_id": body.user_id,
            "book_id": book_id,
            "progress": 0.0,
            "purchase_type": purchase_type,
        }
    )

    logger.info("Conversion pipeline created book %s for user %s (job %s)", book_id, body.user_id, body.processor_job_id)
    return {"book_id": book_id, "processor_job_id": body.processor_job_id, "created": True}
