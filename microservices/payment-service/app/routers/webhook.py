"""
Stripe Webhook Router

Handles incoming webhooks from Stripe for payment status updates.
"""

import logging
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse

from app.services.stripe_service import stripe_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/stripe", tags=["Webhook"])
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    """
    Handle Stripe webhook events.
    
    Stripe sends webhooks for various payment events:
    - payment_intent.succeeded: Payment completed successfully
    - payment_intent.payment_failed: Payment failed
    - checkout.session.completed: Checkout session completed
    - charge.refunded: Refund processed
    
    The webhook signature is verified to ensure the request is from Stripe.
    
    IMPORTANT: This endpoint must return 200 quickly to prevent Stripe retries.
    """
    if not stripe_signature:
        logger.warning("Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
    
    try:
        # Get raw body for signature verification
        payload = await request.body()
        
        # Process webhook
        result = await stripe_service.handle_webhook(payload, stripe_signature)
        
        logger.info(f"Webhook processed successfully: {result}")
        
        return JSONResponse(
            status_code=200,
            content={"received": True, "result": result}
        )
        
    except ValueError as e:
        # Invalid signature or other validation error
        logger.error(f"Webhook validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # Log error but return 200 to prevent Stripe retries
        # (unless you want Stripe to retry)
        logger.error(f"Webhook processing error: {str(e)}")
        # Return 200 to acknowledge receipt even if processing failed
        # The event is stored and can be reprocessed later
        return JSONResponse(
            status_code=200,
            content={"received": True, "error": "Processing error - will retry"}
        )
