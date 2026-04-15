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
from datetime import datetime, timedelta
from bson import ObjectId
from bson.errors import InvalidId

from app.core.config_settings import settings
from app.core.pricing import get_subscription_credit_grant
from app.database.mongodb import MongoDB
from app.services import service_client
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

    def _serialize_payment(self, payment: dict) -> dict:
        """Normalize payment documents for API responses."""
        return {
            "payment_id": str(payment["_id"]),
            "stripe_payment_intent_id": payment.get("stripe_payment_intent_id"),
            "status": payment["status"],
            "amount_cents": payment["amount_cents"],
            "currency": payment["currency"],
            "payment_method": payment["payment_method"],
            "metadata": payment.get("metadata"),
            "created_at": payment.get("created_at"),
            "updated_at": payment.get("updated_at"),
        }

    async def _find_payment(self, payment_reference: str) -> Optional[dict]:
        """Find a payment by internal id, PaymentIntent id, or Checkout Session id."""
        payments = MongoDB.get_db().payments

        try:
            if ObjectId.is_valid(payment_reference):
                payment = await payments.find_one({"_id": ObjectId(payment_reference)})
                if payment:
                    return payment
        except InvalidId:
            pass

        for query in (
            {"stripe_payment_intent_id": payment_reference},
            {"stripe_checkout_session_id": payment_reference},
        ):
            payment = await payments.find_one(query)
            if payment:
                return payment

        return None

    def _map_stripe_payment_status(self, stripe_status: str) -> PaymentStatus:
        status_map = {
            "succeeded": PaymentStatus.SUCCEEDED,
            "processing": PaymentStatus.PROCESSING,
            "requires_payment_method": PaymentStatus.PENDING,
            "requires_action": PaymentStatus.PENDING,
            "requires_confirmation": PaymentStatus.PENDING,
            "canceled": PaymentStatus.CANCELLED,
        }
        return status_map.get(stripe_status, PaymentStatus.PENDING)
    
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

        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data)

        elif event_type == "invoice.payment_succeeded":
            return await self._handle_subscription_invoice_paid(data)

        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data)

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
                
                # If this is a credits or plan purchase with credits, add credits to user account.
                # Use an atomic find_one_and_update to claim the grant so this webhook handler
                # and the /complete-credit-purchase endpoint cannot both fire $inc simultaneously
                # (the previous read→check→write was vulnerable to a race that doubled credits).
                if purchase_type in ("credits", "plan") and "credits" in metadata:
                    try:
                        credits_to_add = int(metadata.get("credits", 0))
                        credit_type = metadata.get("credit_type", "basic")  # Default to basic
                        user_id = payment.get("user_id")
                        
                        if credits_to_add > 0 and user_id:
                            # Determine which credit field to update based on type
                            credit_field = "premium_credits" if credit_type == "premium" else "basic_credits"

                            # Atomically claim the grant — filter ensures only one caller wins.
                            from datetime import datetime as _dt
                            claimed = await MongoDB.get_db().payments.find_one_and_update(
                                {
                                    "stripe_payment_intent_id": payment_intent_id,
                                    "credits_granted": {"$ne": True},
                                },
                                {"$set": {
                                    "credits_granted": True,
                                    "credits_granted_amount": credits_to_add,
                                    "credits_granted_type": credit_type,
                                    "updated_at": _dt.utcnow(),
                                }},
                            )

                            if claimed is None:
                                logger.info(f"Credits already granted for payment {payment_intent_id}, skipping webhook grant")
                            else:
                                # We own the grant — now safely call $inc.
                                await service_client.update_user_credits(user_id, {
                                    credit_field: credits_to_add,
                                    "credits": credits_to_add,  # Legacy total field
                                })
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
        """Handle completed checkout session (payment or subscription mode)"""
        session_id = data.get("id")
        mode = data.get("mode", "payment")

        if mode == "subscription":
            # ── Subscription checkout ────────────────────────────────────────
            metadata = data.get("metadata") or {}
            user_id = metadata.get("user_id")
            plan = metadata.get("plan")
            billing_cycle = metadata.get("billing_cycle", "monthly")
            subscription_id = metadata.get("subscription_id")
            stripe_sub_id = data.get("subscription")

            if user_id and plan:
                subscription_end = datetime.utcnow() + (
                    timedelta(days=365) if billing_cycle == "annual" else timedelta(days=30)
                )
                await service_client.update_user_subscription(user_id, {
                    "subscription_plan": plan,
                    "subscription_status": "active",
                    "subscription_billing_cycle": billing_cycle,
                    "subscription_start_date": datetime.utcnow(),
                    "subscription_end_date": subscription_end,
                    "stripe_subscription_id": stripe_sub_id,
                })
                if subscription_id:
                    try:
                        await MongoDB.get_db().subscriptions.update_one(
                            {"_id": ObjectId(subscription_id)},
                            {
                                "$set": {
                                    "status": "active",
                                    "stripe_subscription_id": stripe_sub_id,
                                    "stripe_checkout_session_id": session_id,
                                    "updated_at": datetime.utcnow(),
                                }
                            },
                        )
                    except Exception as e:
                        logger.error(f"Failed to update internal subscription record: {e}")

            logger.info(f"Subscription checkout completed: {session_id}, user {user_id}, plan {plan}")
            return {"status": "success", "session_id": session_id, "mode": "subscription"}

        else:
            # ── One-time payment checkout ────────────────────────────────────
            payment_intent_id = data.get("payment_intent")
            await MongoDB.get_db().payments.update_one(
                {"stripe_checkout_session_id": session_id},
                {
                    "$set": {
                        "stripe_payment_intent_id": payment_intent_id,
                        "status": PaymentStatus.SUCCEEDED.value,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )
            payment = await MongoDB.get_db().payments.find_one({"stripe_checkout_session_id": session_id})
            if payment:
                await self._create_order(payment)

            logger.info(f"Checkout completed: {session_id}")
            return {"status": "success", "session_id": session_id}

    async def _handle_subscription_updated(self, data: dict) -> Dict[str, Any]:
        """Sync subscription status on plan change or state change."""
        stripe_sub_id = data.get("id")
        if not stripe_sub_id:
            return {"status": "ignored", "reason": "no subscription id"}

        # Fetch the subscription from Stripe to get current status and metadata
        try:
            sub = stripe.Subscription.retrieve(stripe_sub_id)
        except stripe.error.StripeError as e:
            logger.error(f"Failed to retrieve subscription {stripe_sub_id}: {e}")
            return {"status": "error", "error": str(e)}

        status = sub.get("status")  # active | past_due | canceled | ...
        metadata = sub.get("metadata") or {}
        user_id = metadata.get("user_id")

        # Try to find user by stripe_subscription_id if metadata is missing user_id
        if not user_id:
            user = await service_client.get_user_by_stripe_subscription(stripe_sub_id)
            if user:
                user_id = str(user["_id"])

        current_period_end = sub.get("current_period_end")
        end_dt = datetime.utcfromtimestamp(current_period_end) if current_period_end else None
        cancel_at_period_end = bool(sub.get("cancel_at_period_end"))

        if user_id:
            if cancel_at_period_end:
                mapped_status = "pending_cancellation"
            elif status in {"active", "trialing"}:
                mapped_status = "active"
            elif status in {"canceled", "unpaid", "incomplete_expired"}:
                mapped_status = "cancelled"
            else:
                mapped_status = "expired"
            await service_client.update_user_subscription(user_id, {
                "subscription_status": mapped_status,
                "subscription_end_date": end_dt,
            })
            await MongoDB.get_db().subscriptions.update_many(
                {"stripe_subscription_id": stripe_sub_id},
                {
                    "$set": {
                        "status": mapped_status,
                        "updated_at": datetime.utcnow(),
                    }
                },
            )

        logger.info(f"Subscription updated: {stripe_sub_id}, status={status}, user={user_id}")
        return {"status": "synced", "stripe_sub_id": stripe_sub_id, "sub_status": status}

    async def _handle_subscription_invoice_paid(self, data: dict) -> Dict[str, Any]:
        """Grant recurring credits when a subscription invoice is paid."""
        stripe_sub_id = data.get("subscription")
        invoice_id = data.get("id")
        if not stripe_sub_id:
            return {"status": "ignored", "reason": "no subscription id"}

        sync_result = await self._handle_subscription_updated({"id": stripe_sub_id})

        try:
            sub = stripe.Subscription.retrieve(stripe_sub_id)
        except stripe.error.StripeError as exc:
            logger.error(f"Failed to retrieve subscription {stripe_sub_id} for invoice {invoice_id}: {exc}")
            return {"status": "error", "error": str(exc)}

        metadata = sub.get("metadata") or {}
        user_id = metadata.get("user_id")
        plan = metadata.get("plan")

        if not user_id:
            user = await service_client.get_user_by_stripe_subscription(stripe_sub_id)
            if user:
                user_id = str(user["_id"])
                plan = plan or user.get("subscription_plan")

        if user_id and plan and plan != "none":
            try:
                await service_client.update_user_credits(
                    user_id,
                    get_subscription_credit_grant(plan=plan if isinstance(plan, str) else plan),
                )
            except Exception as exc:
                logger.error(f"Failed to grant subscription credits for invoice {invoice_id}: {exc}")
                return {"status": "error", "error": str(exc)}

        return {
            "status": "granted",
            "invoice_id": invoice_id,
            "stripe_sub_id": stripe_sub_id,
            "sync": sync_result,
        }

    async def _handle_subscription_deleted(self, data: dict) -> Dict[str, Any]:
        """Deactivate subscription when cancelled/deleted in Stripe"""
        stripe_sub_id = data.get("id")
        metadata = data.get("metadata") or {}
        user_id = metadata.get("user_id")

        if not user_id:
            user = await service_client.get_user_by_stripe_subscription(stripe_sub_id)
            if user:
                user_id = str(user["_id"])

        if user_id:
            await service_client.update_user_subscription(user_id, {
                "subscription_plan": "none",
                "subscription_status": "cancelled",
                "subscription_cancelled_at": datetime.utcnow(),
            })
            await MongoDB.get_db().subscriptions.update_many(
                {"stripe_subscription_id": stripe_sub_id},
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow()}},
            )

        logger.info(f"Subscription deleted: {stripe_sub_id}, user={user_id}")
        return {"status": "cancelled", "stripe_sub_id": stripe_sub_id}
    
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
        existing_order = await MongoDB.get_db().orders.find_one({"payment_id": str(payment["_id"])})
        if existing_order:
            return str(existing_order["_id"])

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

        # ── Library fulfillment ──────────────────────────────────────────────
        # Collect book IDs from items list OR from metadata (PaymentIntent path)
        book_ids: list = []
        for item in payment.get("items", []):
            bid = item.get("book_id") or item.get("bookId")
            if bid:
                book_ids.append(str(bid))

        if not book_ids:
            # PaymentIntent metadata may store comma-separated book_ids
            raw = (payment.get("metadata") or {}).get("book_ids", "")
            if raw:
                book_ids = [b.strip() for b in raw.split(",") if b.strip()]

        user_id = payment.get("user_id", "")
        for book_id in book_ids:
            try:
                existing = await service_client.get_library_entry(user_id, book_id)
                if not existing:
                    await service_client.add_library_entry(
                        user_id, book_id, progress=0, order_id=order_id,
                        added_at=datetime.utcnow(),
                    )
                    logger.info(f"Added book {book_id} to library for user {user_id}")
            except Exception as lib_err:
                logger.error(f"Failed to add book {book_id} to library for user {user_id}: {lib_err}")

        logger.info(f"Created order {order_id} for user {user_id}")
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
            user = await service_client.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")
            
            basic_credits = user.get("basic_credits", 0)
            premium_credits = user.get("premium_credits", 0)
            user_credits = basic_credits + premium_credits
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
            # Determine which typed credit field to decrement
            # Check metadata for credit_type; fallback to basic_credits
            meta = metadata or {}
            credit_type = meta.get("credit_type")
            inc_payload: dict = {"credits": -total_credits}

            if credit_type == "premium":
                premium_to_use = min(premium_credits, total_credits)
                basic_to_use = total_credits - premium_to_use
                if premium_to_use:
                    inc_payload["premium_credits"] = -premium_to_use
                if basic_to_use:
                    inc_payload["basic_credits"] = -basic_to_use
            elif credit_type == "basic":
                basic_to_use = min(basic_credits, total_credits)
                premium_to_use = total_credits - basic_to_use
                if basic_to_use:
                    inc_payload["basic_credits"] = -basic_to_use
                if premium_to_use:
                    inc_payload["premium_credits"] = -premium_to_use
            else:
                basic_to_use = min(basic_credits, total_credits)
                premium_to_use = total_credits - basic_to_use
                if basic_to_use:
                    inc_payload["basic_credits"] = -basic_to_use
                if premium_to_use:
                    inc_payload["premium_credits"] = -premium_to_use

            # Deduct credits from user via auth-service API
            await service_client.update_user_credits(user_id, inc_payload)
            
            # Get updated credit balance
            remaining_credits = user_credits - total_credits
            
            # Create order
            order_id = await self._create_order(payment_doc | {"_id": result.inserted_id})
            
            logger.info(f"Credits payment processed: {payment_id} for user {user_id} - {total_credits} credits")
            
            return {
                "payment_id": payment_id,
                "order_id": order_id,
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
            payment = await self._find_payment(payment_id)
            if not payment:
                return None

            if payment["status"] in {PaymentStatus.PENDING.value, PaymentStatus.PROCESSING.value}:
                stripe_payment_intent_id = payment.get("stripe_payment_intent_id")
                if stripe_payment_intent_id:
                    intent = await self.get_payment_intent(stripe_payment_intent_id)
                    mapped_status = self._map_stripe_payment_status(intent.status)
                    if mapped_status.value != payment["status"]:
                        await MongoDB.get_db().payments.update_one(
                            {"_id": payment["_id"]},
                            {
                                "$set": {
                                    "status": mapped_status.value,
                                    "updated_at": datetime.utcnow(),
                                }
                            },
                        )
                        payment["status"] = mapped_status.value
                        payment["updated_at"] = datetime.utcnow()
                        if mapped_status == PaymentStatus.SUCCEEDED:
                            await self._create_order(payment)

            return self._serialize_payment(payment)
        except Exception as e:
            logger.error(f"Error getting payment status: {str(e)}")
            return None
    
    async def get_user_payments(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all payments for a user"""
        try:
            cursor = MongoDB.get_db().payments.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
            payments = []
            async for payment in cursor:
                payments.append(self._serialize_payment(payment))
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
