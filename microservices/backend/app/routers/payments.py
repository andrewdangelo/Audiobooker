"""
Payments & Subscriptions Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from datetime import datetime
import logging
import uuid

from app.database.database import get_db
from app.database.db_engine import MongoDBService
from app.models.db_models import Collections
from app.models.schemas import PremiumPurchaseRequest, PremiumPurchaseResponse

logger = logging.getLogger(__name__)
router = APIRouter()


# ============== Premium Purchase Pipeline ==============

@router.post("/store/premium-purchase", response_model=PremiumPurchaseResponse)
async def purchase_premium_book(
    user_id: str = Query(..., description="User ID"),
    purchase_data: PremiumPurchaseRequest = Body(...),
    db = Depends(get_db()),
):
    """
    Purchase the premium (theatrical) edition of an audiobook.

    Two payment methods are supported:
    - ``premium_credits``: Deducts premium credits from the user's balance.
    - ``card``: Assumes a Stripe PaymentIntent has already been confirmed;
      the ``payment_intent_id`` field must be provided.

    On success the premium edition is added (or upgraded) in the user's library
    with ``purchase_type = "premium"``.
    """
    book_id = purchase_data.book_id
    payment_method = purchase_data.payment_method

    # ── Validate book exists and is premium ──────────────────────────────────
    book_service = MongoDBService(db, Collections.BOOKS)
    book = book_service.get_by_id(book_id)

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.get("is_premium", False):
        raise HTTPException(
            status_code=400,
            detail="This book does not have a premium edition",
        )

    premium_credits_required: int = book.get("premium_credits", 2)
    premium_price: float = book.get("premium_price") or 0.0

    # ── Process payment ───────────────────────────────────────────────────────
    credits_used = 0
    amount_charged = 0.0

    if payment_method == "premium_credits":
        # Fetch user's credit balance
        credits_service = MongoDBService(db, Collections.USER_CREDITS)
        user_credits_doc = credits_service.find_one({"user_id": user_id})

        if not user_credits_doc:
            raise HTTPException(status_code=404, detail="User credits record not found")

        # Premium editions can ONLY be purchased with premium credits.
        # Basic credits are explicitly rejected for this payment method.
        available_premium_credits: int = user_credits_doc.get("premium_credits", 0)
        if available_premium_credits < premium_credits_required:
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Insufficient premium credits. "
                    f"Need {premium_credits_required}, have {available_premium_credits}. "
                    "Premium credits are required to purchase theatrical editions — "
                    "basic credits cannot be used for this purchase."
                ),
            )

        # Deduct premium credits only
        new_balance = available_premium_credits - premium_credits_required
        credits_service.update(
            str(user_credits_doc.get("id") or user_credits_doc.get("_id")),
            {
                "premium_credits": new_balance,
                "premium_credits_used": user_credits_doc.get("premium_credits_used", 0) + premium_credits_required,
                "updated_at": datetime.utcnow(),
            },
        )
        credits_used = premium_credits_required

    elif payment_method == "card":
        # Card payment: a Stripe PaymentIntent must have been confirmed client-side.
        # We trust the frontend/payment-service to have validated it; here we
        # just record the charge amount for the activity log.
        if not purchase_data.payment_intent_id:
            raise HTTPException(
                status_code=400,
                detail="payment_intent_id is required for card purchases",
            )
        amount_charged = premium_price

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid payment_method. Use 'premium_credits' or 'card'.",
        )

    # ── Fulfill: add/upgrade library entry ───────────────────────────────────
    library_service = MongoDBService(db, Collections.USER_LIBRARY)
    existing = library_service.find_one({"user_id": user_id, "book_id": book_id})

    if existing:
        # Upgrade existing basic entry to premium
        library_service.update(
            str(existing.get("id") or existing.get("_id")),
            {"purchase_type": "premium", "updated_at": datetime.utcnow()},
        )
    else:
        library_service.create(
            {
                "user_id": user_id,
                "book_id": book_id,
                "progress": 0.0,
                "added_at": datetime.utcnow(),
                "purchase_type": "premium",
            }
        )

    # ── Log activity ─────────────────────────────────────────────────────────
    activity_service = MongoDBService(db, Collections.USER_ACTIVITY)
    activity_service.create(
        {
            "user_id": user_id,
            "activity_type": "premium_purchased",
            "book_id": book_id,
            "title": book.get("title"),
            "meta_data": {
                "payment_method": payment_method,
                "credits_used": credits_used,
                "amount_charged": amount_charged,
            },
        }
    )

    logger.info(
        f"Premium purchase: user={user_id} book={book_id} "
        f"method={payment_method} credits_used={credits_used} amount=${amount_charged:.2f}"
    )

    return PremiumPurchaseResponse(
        success=True,
        book_id=book_id,
        purchase_type="premium",
        credits_used=credits_used,
        amount_charged=amount_charged,
        message="Premium edition added to your library",
    )

