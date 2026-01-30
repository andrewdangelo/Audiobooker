"""
Subscription Router

Endpoints for subscription management including:
- Purchase subscription (with guard for already subscribed)
- Get subscription status
- Cancel subscription (with retention flow)
- Apply retention discount
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Header
from bson import ObjectId

from app.core.config_settings import settings
from app.database.mongodb import MongoDB
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
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Subscription pricing (in cents)
SUBSCRIPTION_PRICES = {
    SubscriptionPlan.BASIC: {
        BillingCycle.MONTHLY: 999,    # $9.99
        BillingCycle.ANNUAL: 9999,    # $99.99 (save ~17%)
    },
    SubscriptionPlan.PREMIUM: {
        BillingCycle.MONTHLY: 1999,   # $19.99
        BillingCycle.ANNUAL: 19999,   # $199.99 (save ~17%)
    }
}

# Retention discount (50% off for 6 months)
RETENTION_DISCOUNT_PERCENTAGE = 50
RETENTION_DISCOUNT_MONTHS = 6


# =========================================================================
# SUBSCRIPTION STATUS
# =========================================================================

@router.get("/status/{user_id}", response_model=SubscriptionStatusResponse, tags=["Subscription"])
async def get_subscription_status(user_id: str):
    """
    Get user's current subscription status.
    """
    try:
        user = await MongoDB.get_user_by_id(user_id)
        
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
        user = await MongoDB.get_user_by_id(request.user_id)
        
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
        
        price_cents = SUBSCRIPTION_PRICES[request.plan][request.billing_cycle]
        
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
        
        # For now, simulate successful subscription (in production, use Stripe)
        # Update user's subscription status
        subscription_end = datetime.utcnow() + (
            timedelta(days=365) if request.billing_cycle == BillingCycle.ANNUAL 
            else timedelta(days=30)
        )
        
        await MongoDB.auth_db.users.update_one(
            {"_id": ObjectId(request.user_id)},
            {
                "$set": {
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
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update subscription record
        await subscriptions.update_one(
            {"_id": ObjectId(subscription_id)},
            {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
        )
        
        # Add monthly credits based on plan
        credit_field = "basic_credits" if request.plan == SubscriptionPlan.BASIC else "premium_credits"
        await MongoDB.auth_db.users.update_one(
            {"_id": ObjectId(request.user_id)},
            {"$inc": {credit_field: 1}}  # Add 1 credit for the subscription
        )
        
        return SubscriptionPurchaseResponse(
            subscription_id=subscription_id,
            checkout_url=None,  # Would be Stripe URL in production
            client_secret=None,
            plan=request.plan,
            billing_cycle=request.billing_cycle,
            amount_cents=price_cents,
            status="active",
            already_subscribed=False,
            message=f"Successfully subscribed to {request.plan.value.capitalize()} plan! "
                   f"Your subscription is active until {subscription_end.strftime('%B %d, %Y')}."
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
        user = await MongoDB.get_user_by_id(request.user_id)
        
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
        current_price = SUBSCRIPTION_PRICES.get(
            SubscriptionPlan(current_plan), 
            {}
        ).get(BillingCycle(billing_cycle), 999)
        
        subscription_end = user.get("subscription_end_date", datetime.utcnow() + timedelta(days=30))
        
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
                
                await MongoDB.auth_db.users.update_one(
                    {"_id": ObjectId(request.user_id)},
                    {
                        "$set": {
                            "subscription_discount_applied": True,
                            "subscription_discount_end_date": discount_end,
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                
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
            await MongoDB.auth_db.users.update_one(
                {"_id": ObjectId(request.user_id)},
                {
                    "$set": {
                        "subscription_status": "pending_cancellation",
                        "subscription_cancelled_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
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
        user = await MongoDB.get_user_by_id(request.user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_status = user.get("subscription_status", "none")
        
        # If pending cancellation, just reactivate
        if current_status == "pending_cancellation":
            await MongoDB.auth_db.users.update_one(
                {"_id": ObjectId(request.user_id)},
                {
                    "$set": {
                        "subscription_status": "active",
                        "subscription_cancelled_at": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
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
        user = await MongoDB.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_plan = user.get("subscription_plan", "none")
        billing_cycle = user.get("subscription_billing_cycle", "monthly")
        
        if current_plan == "none":
            raise HTTPException(status_code=400, detail="User has no subscription to offer discount on")
        
        current_price = SUBSCRIPTION_PRICES.get(
            SubscriptionPlan(current_plan), 
            {}
        ).get(BillingCycle(billing_cycle), 999)
        
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
