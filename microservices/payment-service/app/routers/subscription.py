"""
Subscription Router

Endpoints for subscription management including:
- Purchase subscription (with guard for already subscribed)
- Get subscription status
- Cancel subscription (with retention flow)
- Apply retention discount
"""

import logging
import stripe
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException
from bson import ObjectId

from app.core.config_settings import settings
from app.core.pricing import (
    get_subscription_credit_grant,
    get_subscription_price,
    serialize_credit_pack_catalog,
    serialize_subscription_catalog,
)
from app.database.mongodb import MongoDB
from app.services import service_client
from app.models.schemas import (
    SubscriptionPurchaseRequest,
    SubscriptionPurchaseResponse,
    SubscriptionStatusResponse,
    CancellationRequest,
    CancellationResponse,
    RetentionOffer,
    SubscriptionPlan,
    SubscriptionStatus,
    BillingCycle,
    CancellationStage,
    SubscriptionCatalogItemResponse,
    CreditPackResponse,
)
from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)
# Import side effect ensures Stripe is configured before direct Stripe SDK calls here.
_ = stripe_service

router = APIRouter()

# Retention discount (50% off for 6 months)
RETENTION_DISCOUNT_PERCENTAGE = 50
RETENTION_DISCOUNT_MONTHS = 6


@router.get("/pricing/plans", response_model=list[SubscriptionCatalogItemResponse], tags=["Subscription"])
async def get_subscription_plans():
    """Return the canonical subscription catalog."""
    return serialize_subscription_catalog()


@router.get("/pricing/credit-packs", response_model=list[CreditPackResponse], tags=["Subscription"])
async def get_credit_packs(credit_type: Optional[str] = None):
    """Return the canonical one-time credit pack catalog."""
    if credit_type and credit_type not in {"basic", "premium"}:
        raise HTTPException(status_code=400, detail="credit_type must be 'basic' or 'premium'")
    return serialize_credit_pack_catalog(credit_type)


@router.get("/pricing/credit-packs/{pack_id}", response_model=CreditPackResponse, tags=["Subscription"])
async def get_credit_pack(pack_id: str):
    """Return a single one-time credit pack."""
    pack = next((item for item in serialize_credit_pack_catalog() if item["id"] == pack_id), None)
    if not pack:
        raise HTTPException(status_code=404, detail="Credit pack not found")
    return pack


# =========================================================================
# SUBSCRIPTION STATUS
# =========================================================================

@router.get("/status/{user_id}", response_model=SubscriptionStatusResponse, tags=["Subscription"])
async def get_subscription_status(user_id: str):
    """
    Get user's current subscription status.
    """
    try:
        user = await service_client.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        plan = user.get("subscription_plan", "none")
        status = user.get("subscription_status", "none")
        
        return SubscriptionStatusResponse(
            user_id=user_id,
            subscription_plan=plan,
            subscription_status=status,
            billing_cycle=user.get("subscription_billing_cycle"),
            current_period_end=user.get("subscription_end_date"),
            is_subscribed=status in ["active", "pending_cancellation"],
            discount_applied=user.get("subscription_discount_applied", False),
            discount_end_date=user.get("subscription_discount_end_date")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting subscription status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get subscription status")


# =========================================================================
# SUBSCRIPTION PURCHASE
# =========================================================================

@router.post("/purchase", response_model=SubscriptionPurchaseResponse, tags=["Subscription"])
async def purchase_subscription(request: SubscriptionPurchaseRequest):
    """
    Purchase a subscription plan.
    
    Includes guard to prevent duplicate subscriptions.
    If user is already subscribed to the same plan, returns an error.
    If user is subscribed to a different plan, suggests upgrade/downgrade.
    """
    try:
        # Get user's current subscription status
        user = await service_client.get_user_by_id(request.user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_plan = user.get("subscription_plan", "none")
        current_status = user.get("subscription_status", "none")
        
        # Guard: Check if already subscribed
        if current_status in ["active", "pending_cancellation"]:
            if current_plan == request.plan.value:
                # Already subscribed to the same plan
                return SubscriptionPurchaseResponse(
                    subscription_id="",
                    checkout_url=None,
                    client_secret=None,
                    plan=request.plan,
                    billing_cycle=request.billing_cycle,
                    amount_cents=0,
                    status="already_subscribed",
                    already_subscribed=True,
                    message=f"You are already subscribed to the {request.plan.value.capitalize()} plan. "
                           f"Your subscription is active until {user.get('subscription_end_date', 'your next billing date')}."
                )
            else:
                # Subscribed to a different plan - suggest change
                return SubscriptionPurchaseResponse(
                    subscription_id="",
                    checkout_url=None,
                    client_secret=None,
                    plan=request.plan,
                    billing_cycle=request.billing_cycle,
                    amount_cents=0,
                    status="plan_change_required",
                    already_subscribed=True,
                    message=f"You are currently subscribed to the {current_plan.capitalize()} plan. "
                           f"Please cancel your current subscription first or contact support to change plans."
                )
        
        # Get pricing
        if request.plan == SubscriptionPlan.NONE:
            raise HTTPException(status_code=400, detail="Invalid subscription plan")
        
        price_cents = get_subscription_price(request.plan, request.billing_cycle)
        
        # Apply retention discount if applicable
        if request.apply_discount and user.get("subscription_discount_applied") is False:
            # Check if user is eligible for discount (was previously subscribed)
            if user.get("subscription_cancelled_at"):
                price_cents = int(price_cents * (1 - RETENTION_DISCOUNT_PERCENTAGE / 100))
        
        # Create subscription record
        subscriptions = MongoDB.get_db().subscriptions
        subscription_doc = {
            "user_id": request.user_id,
            "plan": request.plan.value,
            "billing_cycle": request.billing_cycle.value,
            "amount_cents": price_cents,
            "status": "pending",
            "discount_applied": request.apply_discount,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await subscriptions.insert_one(subscription_doc)
        subscription_id = str(result.inserted_id)

        # Determine Stripe Price ID for this plan+cycle
        plan_key = request.plan.value.upper()    # BASIC | PREMIUM | PUBLISHER
        cycle_key = request.billing_cycle.value.upper()  # MONTHLY | ANNUAL
        price_id = getattr(settings, f"STRIPE_{plan_key}_{cycle_key}_PRICE_ID", "")

        if price_id:
            # ── Real Stripe subscription checkout ──────────────────────────
            success_base = request.success_url or settings.PAYMENT_SUCCESS_URL
            cancel_base = request.cancel_url or settings.PAYMENT_CANCEL_URL
            success_url = (
                f"{success_base}"
                f"?purchase_type=subscription"
                f"&session_id={{CHECKOUT_SESSION_ID}}"
                f"&subscription_id={subscription_id}"
                f"&plan={request.plan.value}"
                f"&billing_cycle={request.billing_cycle.value}"
            )
            cancel_url = (
                f"{cancel_base}"
                f"?purchase_type=subscription"
                f"&subscription_id={subscription_id}"
                f"&plan={request.plan.value}"
                f"&billing_cycle={request.billing_cycle.value}"
            )

            session_params: dict = {
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": request.user_id,
                "metadata": {
                    "user_id": request.user_id,
                    "plan": request.plan.value,
                    "billing_cycle": request.billing_cycle.value,
                    "subscription_id": subscription_id,
                },
                "subscription_data": {
                    "metadata": {
                        "user_id": request.user_id,
                        "plan": request.plan.value,
                        "billing_cycle": request.billing_cycle.value,
                        "subscription_id": subscription_id,
                    }
                },
            }

            # Apply retention discount coupon if requested
            if request.apply_discount and user.get("subscription_cancelled_at"):
                coupon = stripe.Coupon.create(
                    percent_off=RETENTION_DISCOUNT_PERCENTAGE,
                    duration="repeating",
                    duration_in_months=RETENTION_DISCOUNT_MONTHS,
                )
                session_params["discounts"] = [{"coupon": coupon.id}]

            try:
                session = stripe.checkout.Session.create(**session_params)
            except stripe.error.StripeError as se:
                logger.error(f"Stripe session creation failed: {se}")
                raise HTTPException(status_code=502, detail="Failed to create Stripe checkout session")

            # Update internal record with session reference
            await subscriptions.update_one(
                {"_id": ObjectId(subscription_id)},
                {
                    "$set": {
                        "stripe_checkout_session_id": session.id,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

            return SubscriptionPurchaseResponse(
                subscription_id=subscription_id,
                checkout_url=session.url,
                client_secret=None,
                plan=request.plan,
                billing_cycle=request.billing_cycle,
                amount_cents=price_cents,
                status="pending",
                already_subscribed=False,
                message=f"Redirecting to checkout for {request.plan.value.capitalize()} plan.",
            )

        else:
            # ── Fallback: simulated activation (dev / no Stripe keys) ──────
            subscription_end = datetime.utcnow() + (
                timedelta(days=365) if request.billing_cycle == BillingCycle.ANNUAL
                else timedelta(days=30)
            )

            await service_client.update_user_subscription(request.user_id, {
                "subscription_plan": request.plan.value,
                "subscription_status": "active",
                "subscription_billing_cycle": request.billing_cycle.value,
                "subscription_start_date": datetime.utcnow(),
                "subscription_end_date": subscription_end,
                "subscription_discount_applied": request.apply_discount,
                "subscription_discount_end_date": (
                    datetime.utcnow() + timedelta(days=30 * RETENTION_DISCOUNT_MONTHS)
                    if request.apply_discount else None
                ),
            })

            # Update subscription record
            await subscriptions.update_one(
                {"_id": ObjectId(subscription_id)},
                {"$set": {"status": "active", "updated_at": datetime.utcnow()}},
            )

            # Add subscription credits (typed field + legacy total)
            await service_client.update_user_credits(request.user_id, get_subscription_credit_grant(request.plan))

            return SubscriptionPurchaseResponse(
                subscription_id=subscription_id,
                checkout_url=None,
                client_secret=None,
                plan=request.plan,
                billing_cycle=request.billing_cycle,
                amount_cents=price_cents,
                status="active",
                already_subscribed=False,
                message=(
                    f"Successfully subscribed to {request.plan.value.capitalize()} plan! "
                    f"Your subscription is active until {subscription_end.strftime('%B %d, %Y')}."
                ),
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error purchasing subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process subscription")


# =========================================================================
# SUBSCRIPTION CANCELLATION (with retention flow)
# =========================================================================

@router.post("/cancel", response_model=CancellationResponse, tags=["Subscription"])
async def cancel_subscription(request: CancellationRequest):
    """
    Handle subscription cancellation with multi-step retention flow.
    
    Flow stages:
    1. INITIAL - User clicks cancel, we show "Are you sure?"
    2. REASON_COLLECTED - User provides reason, we offer discount
    3. DISCOUNT_OFFERED - Show 50% off for 6 months offer
    4. DISCOUNT_ACCEPTED - User accepts discount, apply it
    5. FINAL_CONFIRMATION - User still wants to cancel, final confirmation
    6. CANCELLED - Subscription cancelled (at period end)
    """
    try:
        user = await service_client.get_user_by_id(request.user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_status = user.get("subscription_status", "none")
        current_plan = user.get("subscription_plan", "none")

        if current_status not in ["active", "pending_cancellation"]:
            raise HTTPException(
                status_code=400, 
                detail="No active subscription to cancel"
            )
        
        billing_cycle = user.get("subscription_billing_cycle", "monthly")
        current_price = get_subscription_price(
            SubscriptionPlan(current_plan),
            BillingCycle(billing_cycle),
        )
        
        subscription_end = user.get("subscription_end_date", datetime.utcnow() + timedelta(days=30))
        if isinstance(subscription_end, str):
            try:
                subscription_end = datetime.fromisoformat(subscription_end.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                subscription_end = datetime.utcnow() + timedelta(days=30)
        
        # Stage-based handling
        if request.stage == CancellationStage.INITIAL:
            # First step: Ask if they're sure
            return CancellationResponse(
                user_id=request.user_id,
                stage=CancellationStage.REASON_COLLECTED,
                message="We're sorry to see you go! Before you leave, could you tell us why you're cancelling? "
                       "Your feedback helps us improve.",
                discount_offer=None,
                subscription_ends_at=subscription_end,
                cancelled=False
            )
        
        elif request.stage == CancellationStage.REASON_COLLECTED:
            # Second step: Offer discount
            discounted_price = int(current_price * (1 - RETENTION_DISCOUNT_PERCENTAGE / 100))
            
            discount_offer = {
                "type": "discount",
                "discount_percentage": RETENTION_DISCOUNT_PERCENTAGE,
                "duration_months": RETENTION_DISCOUNT_MONTHS,
                "original_price_cents": current_price,
                "discounted_price_cents": discounted_price,
                "original_price_display": f"${current_price / 100:.2f}",
                "discounted_price_display": f"${discounted_price / 100:.2f}",
                "savings_display": f"${(current_price - discounted_price) / 100:.2f}",
                "message": f"Wait! How about {RETENTION_DISCOUNT_PERCENTAGE}% off for the next "
                          f"{RETENTION_DISCOUNT_MONTHS} months?"
            }
            
            return CancellationResponse(
                user_id=request.user_id,
                stage=CancellationStage.DISCOUNT_OFFERED,
                message=f"🎁 Special Offer: Stay with us and get {RETENTION_DISCOUNT_PERCENTAGE}% off "
                       f"for the next {RETENTION_DISCOUNT_MONTHS} months! "
                       f"That's only ${discounted_price / 100:.2f}/month instead of ${current_price / 100:.2f}.",
                discount_offer=discount_offer,
                subscription_ends_at=subscription_end,
                cancelled=False
            )
        
        elif request.stage == CancellationStage.DISCOUNT_OFFERED:
            if request.accept_discount:
                # User accepted the discount!
                discount_end = datetime.utcnow() + timedelta(days=30 * RETENTION_DISCOUNT_MONTHS)
                
                await service_client.update_user_subscription(request.user_id, {
                    "subscription_discount_applied": True,
                    "subscription_discount_end_date": discount_end,
                })
                
                return CancellationResponse(
                    user_id=request.user_id,
                    stage=CancellationStage.DISCOUNT_ACCEPTED,
                    message=f"🎉 Great choice! Your {RETENTION_DISCOUNT_PERCENTAGE}% discount has been applied "
                           f"for the next {RETENTION_DISCOUNT_MONTHS} months. Thank you for staying with us!",
                    discount_offer=None,
                    subscription_ends_at=subscription_end,
                    cancelled=False
                )
            else:
                # User declined discount, show final confirmation
                return CancellationResponse(
                    user_id=request.user_id,
                    stage=CancellationStage.FINAL_CONFIRMATION,
                    message="We understand. If you're sure you want to cancel, your subscription will remain "
                           f"active until {subscription_end.strftime('%B %d, %Y')}. You'll keep access to all "
                           "your audiobooks and any remaining credits. Are you sure you want to cancel?",
                    discount_offer=None,
                    subscription_ends_at=subscription_end,
                    cancelled=False
                )
        
        elif request.stage == CancellationStage.FINAL_CONFIRMATION:
            # Final cancellation - set to pending_cancellation (cancels at period end)
            stripe_subscription_id = user.get("stripe_subscription_id")
            if stripe_subscription_id:
                try:
                    stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=True)
                except stripe.error.StripeError as exc:
                    logger.error(f"Failed to set cancel_at_period_end for {stripe_subscription_id}: {exc}")
                    raise HTTPException(status_code=502, detail="Failed to cancel Stripe subscription")

            await service_client.update_user_subscription(request.user_id, {
                "subscription_status": "pending_cancellation",
                "subscription_cancelled_at": datetime.utcnow(),
            })
            
            # Update subscription record
            subscriptions = MongoDB.get_db().subscriptions
            await subscriptions.update_one(
                {"user_id": request.user_id, "status": "active"},
                {
                    "$set": {
                        "status": "pending_cancellation",
                        "cancelled_at": datetime.utcnow(),
                        "cancellation_reason": request.reason,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return CancellationResponse(
                user_id=request.user_id,
                stage=CancellationStage.CANCELLED,
                message=f"Your subscription has been cancelled. You'll continue to have access until "
                       f"{subscription_end.strftime('%B %d, %Y')}. We'd love to have you back anytime! "
                       "Your audiobooks and credits will remain in your library.",
                discount_offer=None,
                subscription_ends_at=subscription_end,
                cancelled=True
            )
        
        else:
            raise HTTPException(status_code=400, detail="Invalid cancellation stage")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling subscription: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process cancellation")


# =========================================================================
# RESUBSCRIBE (for cancelled users)
# =========================================================================

@router.post("/resubscribe", response_model=SubscriptionPurchaseResponse, tags=["Subscription"])
async def resubscribe(request: SubscriptionPurchaseRequest):
    """
    Resubscribe a cancelled user.
    
    If user has pending_cancellation status, this will reactivate their subscription.
    If user was previously subscribed, offers retention discount.
    """
    try:
        user = await service_client.get_user_by_id(request.user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_status = user.get("subscription_status", "none")

        # If pending cancellation, just reactivate
        if current_status == "pending_cancellation":
            stripe_subscription_id = user.get("stripe_subscription_id")
            if stripe_subscription_id:
                try:
                    stripe.Subscription.modify(stripe_subscription_id, cancel_at_period_end=False)
                except stripe.error.StripeError as exc:
                    logger.error(f"Failed to reactivate Stripe subscription {stripe_subscription_id}: {exc}")
                    raise HTTPException(status_code=502, detail="Failed to reactivate Stripe subscription")

            await service_client.update_user_subscription(request.user_id, {
                "subscription_status": "active",
                "subscription_cancelled_at": None,
            })
            
            return SubscriptionPurchaseResponse(
                subscription_id="reactivated",
                checkout_url=None,
                client_secret=None,
                plan=SubscriptionPlan(user.get("subscription_plan", "basic")),
                billing_cycle=BillingCycle(user.get("subscription_billing_cycle", "monthly")),
                amount_cents=0,
                status="active",
                already_subscribed=False,
                message="Welcome back! Your subscription has been reactivated. "
                       "We're happy to have you continue with us!"
            )
        
        # Otherwise, process as new subscription (with potential discount)
        return await purchase_subscription(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resubscribing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to resubscribe")


# =========================================================================
# GET RETENTION OFFER
# =========================================================================

@router.get("/retention-offer/{user_id}", response_model=RetentionOffer, tags=["Subscription"])
async def get_retention_offer(user_id: str):
    """
    Get available retention offer for a user.
    
    Returns discount offer details if user is eligible.
    """
    try:
        user = await service_client.get_user_by_id(user_id)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        current_plan = user.get("subscription_plan", "none")
        billing_cycle = user.get("subscription_billing_cycle", "monthly")
        
        if current_plan == "none":
            raise HTTPException(status_code=400, detail="User has no subscription to offer discount on")
        
        current_price = get_subscription_price(
            SubscriptionPlan(current_plan),
            BillingCycle(billing_cycle),
        )
        
        discounted_price = int(current_price * (1 - RETENTION_DISCOUNT_PERCENTAGE / 100))
        
        return RetentionOffer(
            offer_type="discount",
            discount_percentage=RETENTION_DISCOUNT_PERCENTAGE,
            duration_months=RETENTION_DISCOUNT_MONTHS,
            original_price_cents=current_price,
            discounted_price_cents=discounted_price,
            message=f"Stay with us and save {RETENTION_DISCOUNT_PERCENTAGE}% for {RETENTION_DISCOUNT_MONTHS} months! "
                   f"Pay only ${discounted_price / 100:.2f}/month instead of ${current_price / 100:.2f}."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting retention offer: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get retention offer")
