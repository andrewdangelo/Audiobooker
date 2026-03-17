"""
Pydantic Schemas for Payment API requests/responses
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class PaymentStatus(str, Enum):
    """Payment status types"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentMethod(str, Enum):
    """Payment method types"""
    CARD = "card"
    CREDITS = "credits"


class OrderStatus(str, Enum):
    """Order status types"""
    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class SubscriptionPlan(str, Enum):
    """Subscription plan types"""
    NONE = "none"
    BASIC = "basic"
    PREMIUM = "premium"


class SubscriptionStatus(str, Enum):
    """Subscription status types"""
    NONE = "none"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING_CANCELLATION = "pending_cancellation"


class BillingCycle(str, Enum):
    """Billing cycle types"""
    MONTHLY = "monthly"
    ANNUAL = "annual"


class CancellationStage(str, Enum):
    """Stages in the cancellation flow"""
    INITIAL = "initial"
    REASON_COLLECTED = "reason_collected"
    DISCOUNT_OFFERED = "discount_offered"
    DISCOUNT_ACCEPTED = "discount_accepted"
    FINAL_CONFIRMATION = "final_confirmation"
    CANCELLED = "cancelled"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class CartItem(BaseModel):
    """Single item in the cart"""
    book_id: str = Field(..., description="Book ID")
    quantity: int = Field(default=1, ge=1, description="Quantity")
    price_cents: int = Field(..., ge=0, description="Price in cents")
    credits: int = Field(default=1, ge=0, description="Credits required")
    title: str = Field(..., description="Book title for display")


class CreatePaymentIntentRequest(BaseModel):
    """Request to create a Stripe payment intent
    
    Supports two modes:
    1. Cart-based: Provide items array (for audiobook checkout)
    2. Amount-based: Provide amount directly (for subscriptions/credits)
    """
    user_id: str = Field(..., description="User ID from auth service")
    items: Optional[List[CartItem]] = Field(default=None, description="Cart items (optional if amount provided)")
    amount: Optional[int] = Field(default=None, ge=50, description="Amount in cents (optional if items provided)")
    currency: str = Field(default="usd", description="Currency code")
    payment_method: PaymentMethod = Field(default=PaymentMethod.CARD, description="Payment method")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class CreateCheckoutSessionRequest(BaseModel):
    """Request to create a Stripe checkout session"""
    user_id: str = Field(..., description="User ID from auth service")
    items: List[CartItem] = Field(..., min_length=1, description="Cart items")
    success_url: Optional[str] = Field(default=None, description="Override success URL")
    cancel_url: Optional[str] = Field(default=None, description="Override cancel URL")
    customer_email: Optional[str] = Field(default=None, description="Customer email")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class ProcessCreditsPaymentRequest(BaseModel):
    """Request to process payment using credits
    
    Supports two modes:
    1. Cart-based: Provide items array, total_credits calculated from items
    2. Amount-based: Provide amount directly (for subscriptions/credits purchase)
    """
    user_id: str = Field(..., description="User ID from auth service")
    items: Optional[List[CartItem]] = Field(default=None, description="Cart items (optional if amount provided)")
    amount: Optional[int] = Field(default=None, ge=1, description="Amount in cents (optional if items provided)")
    currency: str = Field(default="usd", description="Currency code")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


class RefundPaymentRequest(BaseModel):
    """Request to refund a payment"""
    payment_id: str = Field(..., description="Payment ID")
    reason: Optional[str] = Field(default=None, description="Refund reason")
    amount_cents: Optional[int] = Field(default=None, ge=1, description="Partial refund amount in cents")


class ConfirmPaymentRequest(BaseModel):
    """Request to confirm a payment (for client-side confirmation)"""
    payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    payment_method_id: Optional[str] = Field(default=None, description="Stripe payment method ID")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class PaymentIntentResponse(BaseModel):
    """Response containing Stripe payment intent details"""
    payment_id: str = Field(..., description="Internal payment ID")
    client_secret: str = Field(..., description="Stripe client secret for frontend")
    payment_intent_id: str = Field(..., description="Stripe payment intent ID")
    amount_cents: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code")
    status: PaymentStatus = Field(..., description="Payment status")


class CheckoutSessionResponse(BaseModel):
    """Response containing Stripe checkout session details"""
    session_id: str = Field(..., description="Stripe checkout session ID")
    checkout_url: str = Field(..., description="URL to redirect user for checkout")
    payment_id: str = Field(..., description="Internal payment ID")
    amount_cents: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code")


class CreditsPaymentResponse(BaseModel):
    """Response for credits-based payment"""
    payment_id: str = Field(..., description="Internal payment ID")
    order_id: str = Field(..., description="Order ID")
    credits_deducted: int = Field(..., description="Credits deducted")
    remaining_credits: int = Field(default=0, description="Remaining credits after payment")
    status: PaymentStatus = Field(..., description="Payment status")
    message: str = Field(..., description="Status message")


class PaymentStatusResponse(BaseModel):
    """Response containing payment status"""
    payment_id: str = Field(..., description="Internal payment ID")
    stripe_payment_intent_id: Optional[str] = Field(default=None, description="Stripe payment intent ID")
    status: PaymentStatus = Field(..., description="Payment status")
    amount_cents: int = Field(..., description="Amount in cents")
    currency: str = Field(..., description="Currency code")
    payment_method: PaymentMethod = Field(..., description="Payment method used")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class RefundResponse(BaseModel):
    """Response for refund request"""
    payment_id: str = Field(..., description="Payment ID")
    refund_id: str = Field(..., description="Stripe refund ID")
    amount_cents: int = Field(..., description="Refund amount in cents")
    status: str = Field(..., description="Refund status")


class OrderResponse(BaseModel):
    """Response containing order details"""
    order_id: str = Field(..., description="Order ID")
    user_id: str = Field(..., description="User ID")
    payment_id: str = Field(..., description="Payment ID")
    items: List[CartItem] = Field(..., description="Order items")
    total_cents: int = Field(..., description="Total in cents")
    total_credits: int = Field(..., description="Total credits")
    status: OrderStatus = Field(..., description="Order status")
    payment_method: PaymentMethod = Field(..., description="Payment method used")
    created_at: datetime = Field(..., description="Creation timestamp")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    service: str = Field(..., description="Service name")
    stripe_mode: str = Field(..., description="Stripe mode (sandbox/live)")


class PublishableKeyResponse(BaseModel):
    """Response containing Stripe publishable key"""
    publishable_key: str = Field(..., description="Stripe publishable key for frontend")
    mode: str = Field(..., description="Stripe mode (test/live)")


# ============================================================================
# WEBHOOK MODELS
# ============================================================================

class StripeWebhookEvent(BaseModel):
    """Stripe webhook event data"""
    id: str = Field(..., description="Stripe event ID")
    type: str = Field(..., description="Event type")
    data: dict = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")
    livemode: bool = Field(..., description="Whether event is from live mode")


# ============================================================================
# USER CREDITS MODELS
# ============================================================================

class UserCreditsResponse(BaseModel):
    """Response containing user credits balance"""
    user_id: str = Field(..., description="User ID")
    credits: int = Field(..., description="Current credits balance")


class DeductCreditsRequest(BaseModel):
    """Request to deduct credits from user"""
    user_id: str = Field(..., description="User ID")
    amount: int = Field(..., ge=1, description="Credits to deduct")
    reason: str = Field(..., description="Reason for deduction")
    order_id: Optional[str] = Field(default=None, description="Associated order ID")

# ============================================================================
# SUBSCRIPTION MODELS
# ============================================================================

class SubscriptionPurchaseRequest(BaseModel):
    """Request to purchase a subscription"""
    user_id: str = Field(..., description="User ID from auth service")
    plan: SubscriptionPlan = Field(..., description="Subscription plan to purchase")
    billing_cycle: BillingCycle = Field(default=BillingCycle.MONTHLY, description="Billing cycle")
    customer_email: Optional[str] = Field(default=None, description="Customer email")
    success_url: Optional[str] = Field(default=None, description="Success redirect URL")
    cancel_url: Optional[str] = Field(default=None, description="Cancel redirect URL")
    apply_discount: bool = Field(default=False, description="Whether to apply retention discount")


class SubscriptionPurchaseResponse(BaseModel):
    """Response for subscription purchase"""
    subscription_id: str = Field(..., description="Internal subscription ID")
    checkout_url: Optional[str] = Field(default=None, description="Stripe checkout URL")
    client_secret: Optional[str] = Field(default=None, description="Stripe client secret for embedded checkout")
    plan: SubscriptionPlan = Field(..., description="Subscription plan")
    billing_cycle: BillingCycle = Field(..., description="Billing cycle")
    amount_cents: int = Field(..., description="Amount in cents")
    status: str = Field(..., description="Subscription status")
    already_subscribed: bool = Field(default=False, description="Whether user is already subscribed")
    message: str = Field(..., description="Status message")


class SubscriptionStatusResponse(BaseModel):
    """Response containing subscription status"""
    user_id: str = Field(..., description="User ID")
    subscription_plan: SubscriptionPlan = Field(..., description="Current plan")
    subscription_status: SubscriptionStatus = Field(..., description="Subscription status")
    billing_cycle: Optional[BillingCycle] = Field(default=None, description="Billing cycle")
    current_period_end: Optional[datetime] = Field(default=None, description="When current period ends")
    is_subscribed: bool = Field(..., description="Whether user has active subscription")
    discount_applied: bool = Field(default=False, description="Whether retention discount is applied")
    discount_end_date: Optional[datetime] = Field(default=None, description="When discount period ends")


class CancellationRequest(BaseModel):
    """Request to cancel subscription"""
    user_id: str = Field(..., description="User ID")
    reason: Optional[str] = Field(default=None, description="Cancellation reason")
    stage: CancellationStage = Field(default=CancellationStage.INITIAL, description="Current cancellation stage")
    accept_discount: bool = Field(default=False, description="Whether to accept retention discount")


class CancellationResponse(BaseModel):
    """Response for cancellation request"""
    user_id: str = Field(..., description="User ID")
    stage: CancellationStage = Field(..., description="Current/next cancellation stage")
    message: str = Field(..., description="Message for the user")
    discount_offer: Optional[dict] = Field(default=None, description="Discount offer details")
    subscription_ends_at: Optional[datetime] = Field(default=None, description="When subscription will end")
    cancelled: bool = Field(default=False, description="Whether cancellation is complete")


class RetentionOffer(BaseModel):
    """Retention offer for users trying to cancel"""
    offer_type: str = Field(..., description="Type of offer (discount, pause, etc.)")
    discount_percentage: int = Field(default=50, description="Discount percentage")
    duration_months: int = Field(default=6, description="How long the discount lasts")
    original_price_cents: int = Field(..., description="Original price in cents")
    discounted_price_cents: int = Field(..., description="Discounted price in cents")
    message: str = Field(..., description="Offer message")