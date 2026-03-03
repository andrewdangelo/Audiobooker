"""
Internal Router - Service-to-Service Only

Endpoints called by other microservices (e.g. payment-service) to read/write
user data without direct database access.

All endpoints require the X-Internal-Service-Key header to match the shared
INTERNAL_SERVICE_KEY setting, preventing public access.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel

from app.core.config_settings import settings
from app.database.mongodb import MongoDB

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
# Request / Response schemas
# ---------------------------------------------------------------------------

class SubscriptionUpdate(BaseModel):
    """Fields accepted for a subscription $set update."""
    subscription_plan: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_billing_cycle: Optional[str] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
    subscription_discount_applied: Optional[bool] = None
    subscription_discount_end_date: Optional[datetime] = None
    subscription_cancelled_at: Optional[datetime] = None


class CreditsIncrement(BaseModel):
    """Credit field deltas (positive = add, negative = deduct)."""
    credits: Optional[int] = None           # legacy total
    basic_credits: Optional[int] = None
    premium_credits: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_user(user: dict) -> dict:
    """Convert ObjectId fields to strings for JSON serialisation."""
    user["_id"] = str(user["_id"])
    return user


async def _get_user_or_404(user_id: str) -> dict:
    try:
        oid = ObjectId(user_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    user = await MongoDB.get_db().users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}", tags=["Internal"])
async def get_user_by_id(
    user_id: str,
    _: None = Depends(require_internal_key),
):
    """Return a user document by MongoDB ObjectId."""
    user = await _get_user_or_404(user_id)
    return _serialize_user(user)


@router.get("/users/by-stripe-subscription/{stripe_sub_id}", tags=["Internal"])
async def get_user_by_stripe_subscription(
    stripe_sub_id: str,
    _: None = Depends(require_internal_key),
):
    """Return the user whose stripe_subscription_id matches."""
    user = await MongoDB.get_db().users.find_one({"stripe_subscription_id": stripe_sub_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found for that Stripe subscription")
    return _serialize_user(user)


@router.patch("/users/{user_id}/subscription", tags=["Internal"])
async def update_user_subscription(
    user_id: str,
    body: SubscriptionUpdate,
    _: None = Depends(require_internal_key),
):
    """Overwrite subscription-related fields on a user document ($set)."""
    await _get_user_or_404(user_id)  # validates existence

    set_fields: Dict[str, Any] = {"updated_at": datetime.utcnow()}
    for field, value in body.model_dump(exclude_none=True).items():
        set_fields[field] = value

    try:
        result = await MongoDB.get_db().users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": set_fields},
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    return {"updated": result.modified_count > 0}


@router.patch("/users/{user_id}/credits", tags=["Internal"])
async def update_user_credits(
    user_id: str,
    body: CreditsIncrement,
    _: None = Depends(require_internal_key),
):
    """Atomically increment/decrement credit fields on a user document ($inc)."""
    await _get_user_or_404(user_id)  # validates existence

    inc_fields: Dict[str, Any] = {}
    for field, value in body.model_dump(exclude_none=True).items():
        if value != 0:
            inc_fields[field] = value

    if not inc_fields:
        return {"updated": False, "reason": "no non-zero credit deltas provided"}

    try:
        result = await MongoDB.get_db().users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": inc_fields,
                "$set": {"updated_at": datetime.utcnow()},
            },
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    return {"updated": result.modified_count > 0}
