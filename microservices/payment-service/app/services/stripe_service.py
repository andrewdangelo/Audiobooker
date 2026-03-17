"""
Stripe Payment Service

Handles all Stripe API interactions including:
- Payment Intents (for embedded payment forms)
- Checkout Sessions (for hosted checkout pages)
- Webhooks (for payment status updates)
- Refunds

Automatically uses sandbox/test mode when in development environment.
"""

import stripe
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

from app.core.config_settings import settings
from app.database.mongodb import MongoDB
from app.models.schemas import (
    CartItem, PaymentStatus, PaymentMethod, OrderStatus,
    PaymentIntentResponse, CheckoutSessionResponse, RefundResponse
)

logger = logging.getLogger(__name__)


class StripePaymentService:
    """Stripe payment service with sandbox support"""
    
    def __init__(self):
        """Initialize Stripe with API key"""
        self._configure_stripe()
    
    def _configure_stripe(self):
        """Configure Stripe API with appropriate keys"""
        if not settings.STRIPE_SECRET_KEY:
            logger.warning("Stripe secret key not configured - payments will fail")
            return
        
        stripe.api_key = settings.STRIPE_SECRET_KEY
        stripe.api_version = settings.STRIPE_API_VERSION
        
        mode = "SANDBOX/TEST" if settings.is_sandbox_mode else "LIVE"
        logger.info(f"Stripe configured in {mode} mode")
        
        if not settings.validate_stripe_keys():
            logger.warning("Stripe key mismatch - secret and publishable keys should both be test or both be live")
    
    @property
    def is_sandbox(self) -> bool:
        """Check if running in sandbox mode"""
        return settings.is_sandbox_mode
    
    # =========================================================================
    # PAYMENT INTENT METHODS
    # =========================================================================
    
    async def create_payment_intent(
        self,
        user_id: str,
        items: Optional[List[CartItem]] = None,
        amount: Optional[int] = None,
        currency: str = "usd",
        metadata: Optional[dict] = None
    ) -> PaymentIntentResponse:
        """
        Create a Stripe Payment Intent for embedded payment forms.
        
        This allows you to build your own payment form using Stripe Elements.
        Returns a client_secret to be used on the frontend.
        
        Supports two modes:
        1. Cart-based: Provide items list, amount is calculated from items
        2. Amount-based: Provide amount directly (for subscriptions/credits)
        """
        try:
            # Calculate total - either from items or use provided amount
            if items and len(items) > 0:
                total_cents = sum(item.price_cents * item.quantity for item in items)
                item_count = len(items)
                items_data = [item.model_dump() for item in items]
            elif amount and amount > 0:
                total_cents = amount
                item_count = 1
                items_data = []
            else:
                raise ValueError("Either items or amount must be provided")
            
            if total_cents <= 0:
                raise ValueError("Total amount must be greater than 0")
            
            # Use provided currency or default
            payment_currency = currency or settings.STRIPE_CURRENCY
            
            # Prepare metadata
            payment_metadata = {
                "user_id": user_id,
                "item_count": str(item_count),
                "environment": settings.ENVIRONMENT,
                **(metadata or {})
            }
            
            # Create Stripe Payment Intent
            if not settings.STRIPE_SECRET_KEY:
                raise ValueError("Stripe secret key not configured")
            
            logger.debug(f"Creating payment intent: amount={total_cents}, currency={payment_currency}")
            logger.debug(f"Stripe API Key configured: {bool(stripe.api_key)}, starts with: {stripe.api_key[:15] if stripe.api_key else 'None'}...")
            
            intent = stripe.PaymentIntent.create(
                amount=total_cents,
                currency=payment_currency,
                metadata=payment_metadata,
                automatic_payment_methods={"enabled": True},
            )
            
            if intent is None:
                raise ValueError("Stripe returned None for payment intent")
            
            logger.debug(f"Payment intent created: {intent.id}")
            
            # Store payment record in database
            payment_doc = {
                "user_id": user_id,
                "stripe_payment_intent_id": intent.id,
                "amount_cents": total_cents,
                "currency": payment_currency,
                "status": PaymentStatus.PENDING.value,
                "payment_method": PaymentMethod.CARD.value,
                "items": items_data,
                "metadata": payment_metadata,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            result = await MongoDB.get_db().payments.insert_one(payment_doc)
            payment_id = str(result.inserted_id)
            
            logger.info(f"Created payment intent {intent.id} for user {user_id} - Amount: {total_cents} cents")
            
            return PaymentIntentResponse(
                payment_id=payment_id,
                client_secret=intent.client_secret,
                payment_intent_id=intent.id,
                amount_cents=total_cents,
                currency=payment_currency,
                status=PaymentStatus.PENDING
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating payment intent: {str(e)}")
            raise
    
    async def confirm_payment_intent(
        self,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None
    ) -> PaymentStatus:
        """Confirm a payment intent (for server-side confirmation if needed)"""
        try:
            params = {}
            if payment_method_id:
                params["payment_method"] = payment_method_id
            
            intent = stripe.PaymentIntent.confirm(payment_intent_id, **params)
            
            # Map Stripe status to our status
            status_map = {
                "succeeded": PaymentStatus.SUCCEEDED,
                "processing": PaymentStatus.PROCESSING,
                "requires_payment_method": PaymentStatus.PENDING,
                "requires_action": PaymentStatus.PENDING,
                "canceled": PaymentStatus.CANCELLED,
            }
            
            return status_map.get(intent.status, PaymentStatus.PENDING)
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {str(e)}")
            raise
    
    async def get_payment_intent(self, payment_intent_id: str) -> dict:
        """Retrieve a payment intent from Stripe"""
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving payment intent: {str(e)}")
            raise
    
    # =========================================================================
    # CHECKOUT SESSION METHODS
    # =========================================================================
    
    async def create_checkout_session(
        self,
        user_id: str,
        items: List[CartItem],
        customer_email: Optional[str] = None,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> CheckoutSessionResponse:
        """
        Create a Stripe Checkout Session for hosted checkout.
        
        This redirects the user to Stripe's hosted checkout page.
        Simpler integration but less customizable.
        """
        try:
            # Build line items
            line_items = []
            for item in items:
                line_items.append({
                    "price_data": {
                        "currency": settings.STRIPE_CURRENCY,
                        "product_data": {
                            "name": item.title,
                            "metadata": {"book_id": item.book_id}
                        },
                        "unit_amount": item.price_cents,
                    },
                    "quantity": item.quantity,
                })
            
            # Calculate total
            total_cents = sum(item.price_cents * item.quantity for item in items)
            
            # Prepare metadata
            session_metadata = {
                "user_id": user_id,
                "item_count": str(len(items)),
                "environment": settings.ENVIRONMENT,
                **(metadata or {})
            }
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                mode="payment",
                line_items=line_items,
                success_url=success_url or settings.PAYMENT_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=cancel_url or settings.PAYMENT_CANCEL_URL,
                customer_email=customer_email,
                metadata=session_metadata,
            )
            
            # Store payment record
            payment_doc = {
                "user_id": user_id,
                "stripe_checkout_session_id": session.id,
                "amount_cents": total_cents,
                "currency": settings.STRIPE_CURRENCY,
                "status": PaymentStatus.PENDING.value,
                "payment_method": PaymentMethod.CARD.value,
                "items": [item.model_dump() for item in items],
                "metadata": session_metadata,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            result = await MongoDB.get_db().payments.insert_one(payment_doc)
            payment_id = str(result.inserted_id)
            
            logger.info(f"Created checkout session {session.id} for user {user_id}")
            
            return CheckoutSessionResponse(
                session_id=session.id,
                checkout_url=session.url,
                payment_id=payment_id,
                amount_cents=total_cents,
                currency=settings.STRIPE_CURRENCY
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating checkout session: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            raise
    
    async def get_checkout_session(self, session_id: str) -> dict:
        """Retrieve a checkout session from Stripe"""
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving checkout session: {str(e)}")
            raise
    
    # =========================================================================
    # WEBHOOK HANDLING
    # =========================================================================
    
    async def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        
        Verifies the webhook signature and processes the event.
        """
        try:
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET
            )
            
            # Check for duplicate event (idempotency)
            existing = await MongoDB.get_db().webhook_events.find_one({"stripe_event_id": event.id})
            if existing:
                logger.info(f"Duplicate webhook event {event.id} - skipping")
                return {"status": "duplicate", "event_id": event.id}
            
            # Store event for idempotency
            await MongoDB.get_db().webhook_events.insert_one({
                "stripe_event_id": event.id,
                "event_type": event.type,
                "livemode": event.livemode,
                "created_at": datetime.utcnow(),
                "processed": False
            })
            
            # Handle specific event types
            result = await self._process_webhook_event(event)
            
            # Mark event as processed
            await MongoDB.get_db().webhook_events.update_one(
                {"stripe_event_id": event.id},
                {"$set": {"processed": True, "processed_at": datetime.utcnow()}}
            )
            
            return result
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {str(e)}")
            raise ValueError("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            raise
    
    async def _process_webhook_event(self, event: stripe.Event) -> Dict[str, Any]:
        """Process different webhook event types"""
        event_type = event.type
        data = event.data.object
        
        logger.info(f"Processing webhook event: {event_type}")
        
        if event_type == "payment_intent.succeeded":
            return await self._handle_payment_succeeded(data)
        
        elif event_type == "payment_intent.payment_failed":
            return await self._handle_payment_failed(data)
        
        elif event_type == "checkout.session.completed":
            return await self._handle_checkout_completed(data)
        
        elif event_type == "charge.refunded":
            return await self._handle_refund(data)
        
        else:
            logger.info(f"Unhandled webhook event type: {event_type}")
            return {"status": "ignored", "event_type": event_type}
    
    async def _handle_payment_succeeded(self, data: dict) -> Dict[str, Any]:
        """Handle successful payment"""
        payment_intent_id = data.get("id")
        
        # Update payment record
        result = await MongoDB.get_db().payments.update_one(
            {"stripe_payment_intent_id": payment_intent_id},
            {
                "$set": {
                    "status": PaymentStatus.SUCCEEDED.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            # Get payment details to check if this was a credit purchase
            payment = await MongoDB.get_db().payments.find_one({"stripe_payment_intent_id": payment_intent_id})
            if payment:
                # Check if this is a credit purchase by looking at metadata
                metadata = payment.get("metadata", {})
                purchase_type = metadata.get("purchase_type")
                
                # If this is a credits or plan purchase with credits, add credits to user account
                if purchase_type in ("credits", "plan") and "credits" in metadata:
                    try:
                        credits_to_add = int(metadata.get("credits", 0))
                        credit_type = metadata.get("credit_type", "basic")  # Default to basic
                        user_id = payment.get("user_id")
                        
                        if credits_to_add > 0 and user_id:
                            # Determine which credit field to update based on type
                            credit_field = "premium_credits" if credit_type == "premium" else "basic_credits"
                            
                            # Add credits to user in auth database
                            await MongoDB.get_auth_db().users.update_one(
                                {"_id": ObjectId(user_id)},
                                {
                                    "$inc": {
                                        credit_field: credits_to_add,
                                        "credits": credits_to_add  # Legacy total field
                                    },
                                    "$set": {"updated_at": datetime.utcnow()}
                                }
                            )
                            logger.info(f"Added {credits_to_add} {credit_type} credits to user {user_id} from payment {payment_intent_id}")
                    except Exception as e:
                        logger.error(f"Failed to add credits to user: {str(e)}")
                
                # Create order record
                await self._create_order(payment)
        
        logger.info(f"Payment succeeded: {payment_intent_id}")
        return {"status": "success", "payment_intent_id": payment_intent_id}
    
    async def _handle_payment_failed(self, data: dict) -> Dict[str, Any]:
        """Handle failed payment"""
        payment_intent_id = data.get("id")
        error_message = data.get("last_payment_error", {}).get("message", "Unknown error")
        
        await MongoDB.get_db().payments.update_one(
            {"stripe_payment_intent_id": payment_intent_id},
            {
                "$set": {
                    "status": PaymentStatus.FAILED.value,
                    "error_message": error_message,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        logger.warning(f"Payment failed: {payment_intent_id} - {error_message}")
        return {"status": "failed", "payment_intent_id": payment_intent_id, "error": error_message}
    
    async def _handle_checkout_completed(self, data: dict) -> Dict[str, Any]:
        """Handle completed checkout session"""
        session_id = data.get("id")
        payment_intent_id = data.get("payment_intent")
        
        # Update payment record
        await MongoDB.get_db().payments.update_one(
            {"stripe_checkout_session_id": session_id},
            {
                "$set": {
                    "stripe_payment_intent_id": payment_intent_id,
                    "status": PaymentStatus.SUCCEEDED.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Create order
        payment = await MongoDB.get_db().payments.find_one({"stripe_checkout_session_id": session_id})
        if payment:
            await self._create_order(payment)
        
        logger.info(f"Checkout completed: {session_id}")
        return {"status": "success", "session_id": session_id}
    
    async def _handle_refund(self, data: dict) -> Dict[str, Any]:
        """Handle refund event"""
        payment_intent_id = data.get("payment_intent")
        
        await MongoDB.get_db().payments.update_one(
            {"stripe_payment_intent_id": payment_intent_id},
            {
                "$set": {
                    "status": PaymentStatus.REFUNDED.value,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Update order status
        await MongoDB.get_db().orders.update_one(
            {"payment_intent_id": payment_intent_id},
            {"$set": {"status": OrderStatus.REFUNDED.value, "updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"Payment refunded: {payment_intent_id}")
        return {"status": "refunded", "payment_intent_id": payment_intent_id}
    
    async def _create_order(self, payment: dict) -> str:
        """Create an order record from a successful payment"""
        order_doc = {
            "user_id": payment["user_id"],
            "payment_id": str(payment["_id"]),
            "stripe_payment_intent_id": payment.get("stripe_payment_intent_id"),
            "items": payment["items"],
            "total_cents": payment["amount_cents"],
            "total_credits": sum(item.get("credits", 1) * item.get("quantity", 1) for item in payment["items"]),
            "status": OrderStatus.PAID.value,
            "payment_method": payment["payment_method"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        result = await MongoDB.get_db().orders.insert_one(order_doc)
        order_id = str(result.inserted_id)
        
        logger.info(f"Created order {order_id} for user {payment['user_id']}")
        return order_id
    
    # =========================================================================
    # REFUND METHODS
    # =========================================================================
    
    async def create_refund(
        self,
        payment_id: str,
        amount_cents: Optional[int] = None,
        reason: Optional[str] = None
    ) -> RefundResponse:
        """Create a refund for a payment"""
        try:
            # Get payment record
            payment = await MongoDB.get_db().payments.find_one({"_id": ObjectId(payment_id)})
            if not payment:
                raise ValueError("Payment not found")
            
            payment_intent_id = payment.get("stripe_payment_intent_id")
            if not payment_intent_id:
                raise ValueError("No Stripe payment intent found for this payment")
            
            # Create refund
            refund_params = {"payment_intent": payment_intent_id}
            if amount_cents:
                refund_params["amount"] = amount_cents
            if reason:
                refund_params["reason"] = "requested_by_customer"
                refund_params["metadata"] = {"reason": reason}
            
            refund = stripe.Refund.create(**refund_params)
            
            # Update payment status
            await MongoDB.get_db().payments.update_one(
                {"_id": ObjectId(payment_id)},
                {
                    "$set": {
                        "status": PaymentStatus.REFUNDED.value,
                        "refund_id": refund.id,
                        "refund_amount": refund.amount,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Refund created: {refund.id} for payment {payment_id}")
            
            return RefundResponse(
                payment_id=payment_id,
                refund_id=refund.id,
                amount_cents=refund.amount,
                status=refund.status
            )
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {str(e)}")
            raise
    
    # =========================================================================
    # CREDITS PAYMENT (Non-Stripe)
    # =========================================================================
    
    async def process_credits_payment(
        self,
        user_id: str,
        items: Optional[List[CartItem]] = None,
        amount: Optional[int] = None,
        currency: str = "usd",
        metadata: Optional[dict] = None
    ) -> Dict[str, Any]:
        """
        Process a payment using user credits instead of card.
        
        This is handled internally without Stripe.
        Credits are deducted from the user's account in the auth service.
        
        Supports two modes:
        1. Cart-based: Provide items list, totals calculated from items
        2. Amount-based: Provide amount directly (for subscriptions/credits)
        """
        try:
            # Calculate totals - either from items or use provided amount
            if items and len(items) > 0:
                total_cents = sum(item.price_cents * item.quantity for item in items)
                total_credits = sum(item.credits * item.quantity for item in items)
                items_data = [item.model_dump() for item in items]
            elif amount and amount > 0:
                total_cents = amount
                # Convert cents to credits (1 credit = 100 cents = $1)
                total_credits = amount // 100 if amount >= 100 else 1
                items_data = []
            else:
                raise ValueError("Either items or amount must be provided")
            
            # Verify user exists and has enough credits
            user = await MongoDB.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            user_credits = user.get("credits", 0)
            if user_credits < total_credits:
                raise ValueError(f"Insufficient credits. Required: {total_credits}, Available: {user_credits}")
            
            # Create payment record
            payment_doc = {
                "user_id": user_id,
                "amount_cents": total_cents,
                "credits_used": total_credits,
                "currency": currency or settings.STRIPE_CURRENCY,
                "status": PaymentStatus.SUCCEEDED.value,
                "payment_method": PaymentMethod.CREDITS.value,
                "items": items_data,
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            
            result = await MongoDB.get_db().payments.insert_one(payment_doc)
            payment_id = str(result.inserted_id)
            
            # Deduct credits from user (update auth database)
            await MongoDB.get_auth_db().users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$inc": {"credits": -total_credits},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            # Get updated credit balance
            remaining_credits = user_credits - total_credits
            
            # Create order
            await self._create_order(payment_doc | {"_id": result.inserted_id})
            
            logger.info(f"Credits payment processed: {payment_id} for user {user_id} - {total_credits} credits")
            
            return {
                "payment_id": payment_id,
                "order_id": payment_id,  # Using payment_id as order_id for now
                "credits_deducted": total_credits,
                "remaining_credits": remaining_credits,
                "status": PaymentStatus.SUCCEEDED.value,
                "message": "Payment successful using credits"
            }
            
        except Exception as e:
            logger.error(f"Error processing credits payment: {str(e)}")
            raise
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    async def get_payment_status(self, payment_id: str) -> Optional[dict]:
        """Get payment status from database"""
        try:
            payment = await MongoDB.get_db().payments.find_one({"_id": ObjectId(payment_id)})
            if payment:
                payment["_id"] = str(payment["_id"])
            return payment
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return None
    
    async def get_user_payments(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all payments for a user"""
        try:
            cursor = MongoDB.get_db().payments.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            payments = []
            async for payment in cursor:
                payment["_id"] = str(payment["_id"])
                payments.append(payment)
            return payments
        except Exception as e:
            logger.error(f"Error getting user payments: {str(e)}")
            return []
    
    async def get_user_orders(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all orders for a user"""
        try:
            cursor = MongoDB.get_db().orders.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            orders = []
            async for order in cursor:
                order["_id"] = str(order["_id"])
                orders.append(order)
            return orders
        except Exception as e:
            logger.error(f"Error getting user orders: {str(e)}")
            return []


# Singleton instance
stripe_service = StripePaymentService()
