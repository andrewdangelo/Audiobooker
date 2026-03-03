"""
Payment Router

Endpoints for payment processing including:
- Create payment intent (for Stripe Elements)
- Create checkout session (for Stripe Hosted Checkout)
- Get publishable key
- Payment status
- User payments and orders
- Credits payment
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse
from bson import ObjectId

from app.core.config_settings import settings
from app.services.stripe_service import stripe_service
from app.database.mongodb import MongoDB
from app.services import service_client
from app.models.schemas import (
    CreatePaymentIntentRequest,
    CreateCheckoutSessionRequest,
    ProcessCreditsPaymentRequest,
    RefundPaymentRequest,
    ConfirmPaymentRequest,
    PaymentIntentResponse,
    CheckoutSessionResponse,
    CreditsPaymentResponse,
    PaymentStatusResponse,
    RefundResponse,
    PublishableKeyResponse,
    PaymentStatus,
    PaymentMethod,
    OrderResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =========================================================================
# CONFIG ENDPOINTS
# =========================================================================

@router.get("/config/publishable-key", response_model=PublishableKeyResponse, tags=["Config"])
async def get_publishable_key():
    """
    Get the Stripe publishable key for frontend initialization.
    
    This key is safe to expose on the frontend.
    Returns different keys based on environment (test/live).
    """
    if not settings.STRIPE_PUBLISHABLE_KEY:
        raise HTTPException(
            status_code=500,
            detail="Stripe publishable key not configured"
        )
    
    mode = "test" if settings.is_sandbox_mode else "live"
    
    return PublishableKeyResponse(
        publishable_key=settings.STRIPE_PUBLISHABLE_KEY,
        mode=mode
    )


# =========================================================================
# PAYMENT INTENT ENDPOINTS
# =========================================================================

@router.post("/create-payment-intent", response_model=PaymentIntentResponse, tags=["Payment"])
async def create_payment_intent(request: CreatePaymentIntentRequest):
    """
    Create a Stripe Payment Intent for embedded payment forms.
    
    Use this when you want to build a custom payment form using Stripe Elements.
    Returns a client_secret that the frontend uses to complete the payment.
    
    Supports two modes:
    1. Cart-based: Provide items array (for audiobook checkout)
    2. Amount-based: Provide amount directly (for subscriptions/credits)
    
    Flow:
    1. Frontend calls this endpoint with cart items or amount
    2. Backend creates Payment Intent and stores payment record
    3. Frontend uses client_secret with Stripe.js to collect payment
    4. Stripe sends webhook when payment succeeds/fails
    """
    try:
        # Validate that either items or amount is provided
        if not request.items and not request.amount:
            raise HTTPException(
                status_code=400, 
                detail="Either 'items' or 'amount' must be provided"
            )
        
        result = await stripe_service.create_payment_intent(
            user_id=request.user_id,
            items=request.items,
            amount=request.amount,
            currency=request.currency,
            metadata=request.metadata
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create payment intent")


@router.post("/confirm-payment", tags=["Payment"])
async def confirm_payment(request: ConfirmPaymentRequest):
    """
    Confirm a payment intent (server-side confirmation).
    
    This is typically not needed as Stripe.js handles confirmation on the frontend.
    Use only for specific server-side confirmation flows.
    """
    try:
        status = await stripe_service.confirm_payment_intent(
            payment_intent_id=request.payment_intent_id,
            payment_method_id=request.payment_method_id
        )
        return {"status": status.value, "payment_intent_id": request.payment_intent_id}
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to confirm payment")


# =========================================================================
# CHECKOUT SESSION ENDPOINTS
# =========================================================================

@router.post("/create-checkout-session", response_model=CheckoutSessionResponse, tags=["Checkout"])
async def create_checkout_session(request: CreateCheckoutSessionRequest):
    """
    Create a Stripe Checkout Session for hosted checkout.
    
    Use this when you want Stripe to handle the entire checkout UI.
    Returns a URL to redirect the user to Stripe's hosted checkout page.
    
    Flow:
    1. Frontend calls this endpoint with cart items
    2. Backend creates Checkout Session and stores payment record
    3. Frontend redirects user to checkout_url
    4. User completes payment on Stripe's page
    5. Stripe redirects to success_url or cancel_url
    6. Stripe sends webhook when payment succeeds
    """
    try:
        result = await stripe_service.create_checkout_session(
            user_id=request.user_id,
            items=request.items,
            customer_email=request.customer_email,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata=request.metadata
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.get("/checkout-session/{session_id}", tags=["Checkout"])
async def get_checkout_session(session_id: str):
    """
    Get details of a checkout session.
    
    Use this to verify payment status after redirect from Stripe checkout.
    """
    try:
        session = await stripe_service.get_checkout_session(session_id)
        return {
            "session_id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "amount_total": session.amount_total,
            "currency": session.currency,
        }
    except Exception as e:
        logger.error(f"Error getting checkout session: {str(e)}")
        raise HTTPException(status_code=404, detail="Checkout session not found")


# =========================================================================
# CREDITS PAYMENT ENDPOINTS
# =========================================================================

@router.post("/pay-with-credits", response_model=CreditsPaymentResponse, tags=["Credits"])
async def pay_with_credits(request: ProcessCreditsPaymentRequest):
    """
    Process payment using user credits instead of card.
    
    This is an internal payment method that doesn't use Stripe.
    Credits are deducted from the user's account.
    
    Supports two modes:
    1. Cart-based: Provide items array (for audiobook checkout)
    2. Amount-based: Provide amount directly (for subscriptions/credits)
    
    Flow:
    1. Frontend calls this endpoint with cart items or amount
    2. Backend verifies user has enough credits
    3. Backend deducts credits and creates order
    4. User receives purchased items immediately
    """
    try:
        # Validate that either items or amount is provided
        if not request.items and not request.amount:
            raise HTTPException(
                status_code=400, 
                detail="Either 'items' or 'amount' must be provided"
            )
        
        result = await stripe_service.process_credits_payment(
            user_id=request.user_id,
            items=request.items,
            amount=request.amount,
            currency=request.currency,
            metadata=request.metadata
        )
        return CreditsPaymentResponse(
            payment_id=result["payment_id"],
            order_id=result.get("order_id", ""),
            credits_deducted=result["credits_deducted"],
            remaining_credits=result.get("remaining_credits", 0),
            status=PaymentStatus(result["status"]),
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing credits payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process credits payment")


# =========================================================================
# COMPLETE CREDIT PURCHASE (called by frontend after Stripe payment succeeds)
# =========================================================================

@router.post("/complete-credit-purchase", tags=["Credits"])
async def complete_credit_purchase(body: dict):
    """
    Synchronously grant credits after a successful Stripe payment intent.

    Called by the frontend immediately after Stripe.js confirms the payment,
    so credits are in the DB before the success page fetches the user profile.
    Idempotent — safe to call multiple times for the same payment intent.
    """
    from datetime import datetime

    payment_intent_id = body.get("payment_intent_id")
    if not payment_intent_id:
        raise HTTPException(status_code=400, detail="payment_intent_id is required")

    payment = await MongoDB.get_db().payments.find_one(
        {"stripe_payment_intent_id": payment_intent_id}
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Idempotency guard — don't double-grant
    if payment.get("credits_granted"):
        return {
            "status": "already_granted",
            "credits_added": payment.get("credits_granted_amount", 0),
            "credit_type": payment.get("credits_granted_type", "basic"),
        }

    metadata = payment.get("metadata", {})
    purchase_type = metadata.get("purchase_type")
    if purchase_type not in ("credits", "plan"):
        raise HTTPException(
            status_code=400,
            detail=f"Not a credit purchase (purchase_type={purchase_type})",
        )

    credits_to_add = int(metadata.get("credits", 0))
    credit_type = metadata.get("credit_type", "basic")
    user_id = payment.get("user_id")

    if credits_to_add <= 0:
        raise HTTPException(status_code=400, detail="No credits to add for this payment")
    if not user_id:
        raise HTTPException(status_code=400, detail="No user_id on payment record")

    credit_field = "premium_credits" if credit_type == "premium" else "basic_credits"
    updated = await service_client.update_user_credits(user_id, {
        credit_field: credits_to_add,
        "credits": credits_to_add,
    })

    if not updated:
        raise HTTPException(status_code=502, detail="Failed to update user credits")

    # Mark as granted so the webhook doesn't double-count
    await MongoDB.get_db().payments.update_one(
        {"stripe_payment_intent_id": payment_intent_id},
        {"$set": {
            "credits_granted": True,
            "credits_granted_amount": credits_to_add,
            "credits_granted_type": credit_type,
            "status": "succeeded",
            "updated_at": datetime.utcnow(),
        }},
    )

    logger.info(f"Granted {credits_to_add} {credit_type} credits to user {user_id} for payment {payment_intent_id}")
    return {
        "status": "granted",
        "credits_added": credits_to_add,
        "credit_type": credit_type,
    }


# =========================================================================
# PAYMENT STATUS ENDPOINTS
# =========================================================================

@router.get("/payment/{payment_id}", tags=["Payment"])
async def get_payment_status(payment_id: str):
    """
    Get the status of a payment by ID.
    """
    try:
        payment = await stripe_service.get_payment_status(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        return payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting payment status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get payment status")


@router.get("/user/{user_id}/payments", tags=["User"])
async def get_user_payments(user_id: str, limit: int = 50):
    """
    Get all payments for a user.
    """
    try:
        payments = await stripe_service.get_user_payments(user_id, limit)
        return {"payments": payments, "count": len(payments)}
    except Exception as e:
        logger.error(f"Error getting user payments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user payments")


@router.get("/user/{user_id}/orders", tags=["User"])
async def get_user_orders(user_id: str, limit: int = 50):
    """
    Get all orders for a user.
    """
    try:
        orders = await stripe_service.get_user_orders(user_id, limit)
        normalized_orders = []
        for order in orders:
            normalized_orders.append(
                {
                    "order_id": order["_id"],
                    "user_id": order["user_id"],
                    "payment_id": order["payment_id"],
                    "items": order.get("items", []),
                    "total_cents": order.get("total_cents", 0),
                    "total_credits": order.get("total_credits", 0),
                    "status": order.get("status"),
                    "payment_method": order.get("payment_method"),
                    "created_at": order.get("created_at"),
                }
            )
        return {"orders": normalized_orders, "count": len(normalized_orders)}
    except Exception as e:
        logger.error(f"Error getting user orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user orders")


# =========================================================================
# REFUND ENDPOINTS
# =========================================================================

@router.post("/refund", response_model=RefundResponse, tags=["Refund"])
async def create_refund(request: RefundPaymentRequest):
    """
    Create a refund for a payment.
    
    Can create full or partial refunds.
    """
    try:
        result = await stripe_service.create_refund(
            payment_id=request.payment_id,
            amount_cents=request.amount_cents,
            reason=request.reason
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating refund: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create refund")


@router.post("/admin/process-payment/{payment_id}", tags=["Admin"])
async def manually_process_payment(payment_id: str):
    """
    Manually process a payment and add credits
    (For testing when webhooks don't fire)
    """
    try:
        from app.database.mongodb import MongoDB
        from app.services import service_client
        
        # Get payment
        payment = await MongoDB.get_db().payments.find_one({"_id": ObjectId(payment_id)})
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")
        
        # Check if this is a credit purchase
        metadata = payment.get("metadata", {})
        purchase_type = metadata.get("purchase_type")
        
        # Handle both "credits" and "plan" purchase types (both can add credits)
        if purchase_type not in ("credits", "plan"):
            return {"message": f"Not a credit purchase (type: {purchase_type})", "payment_id": payment_id}
        
        credits_to_add = int(metadata.get("credits", 0))
        credit_type = metadata.get("credit_type", "basic")
        user_id = payment.get("user_id")
        
        if credits_to_add <= 0:
            raise HTTPException(status_code=400, detail="No credits to add")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="No user_id in payment")
        
        # Determine which credit field to update
        credit_field = "premium_credits" if credit_type == "premium" else "basic_credits"
        
        # Add credits to user via auth-service API
        updated = await service_client.update_user_credits(user_id, {
            credit_field: credits_to_add,
            "credits": credits_to_add,  # Legacy total
        })

        if updated:
            logger.info(f"Manually added {credits_to_add} {credit_type} credits to user {user_id}")
            return {
                "status": "success",
                "message": f"Added {credits_to_add} {credit_type} credits to user",
                "user_id": user_id,
                "credits_added": credits_to_add,
                "credit_type": credit_type
            }
        else:
            raise HTTPException(status_code=404, detail="User not found")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing payment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

