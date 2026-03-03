"""
Internal Router - Service-to-Service Only

Endpoints called by other microservices (e.g. payment-service) to read/write
backend data without direct database access.

All endpoints require the X-Internal-Service-Key header to match the shared
INTERNAL_SERVICE_KEY setting, preventing public access.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

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
