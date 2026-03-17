# Payment Service Integration Guide

This guide explains how to integrate the payment service with the frontend checkout flow.

## Overview

The payment service supports two main payment flows:

1. **Card Payment (Stripe)** - Using Stripe Payment Intents or Checkout Sessions
2. **Credits Payment** - Using user account credits

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Checkout.tsx                           │   │
│  │                                                           │   │
│  │  1. User selects payment method                          │   │
│  │  2. If card: → createPaymentIntent() or checkoutSession()│   │
│  │  3. If credits: → payWithCredits()                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API Proxy (:8009)                         │
│  /api/v1/audiobooker_proxy/payment/* → Payment Service          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Payment Service (:8004)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  /create-payment-intent  │  /pay-with-credits           │   │
│  │  /create-checkout-session│  /refund                      │   │
│  │  /webhook/stripe         │  /user/{id}/payments          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│      Stripe API         │     │       MongoDB           │
│  (sandbox in dev)       │     │  payments, orders       │
└─────────────────────────┘     └─────────────────────────┘
                                          │
                                          ▼
                              ┌─────────────────────────┐
                              │   Auth Service MongoDB   │
                              │   (user credits lookup)  │
                              └─────────────────────────┘
```

## Frontend Integration Steps

### Step 1: Install Stripe.js

```bash
npm install @stripe/stripe-js @stripe/react-stripe-js
```

### Step 2: Create Payment Service

Create a new service file for payment API calls:

```typescript
// src/services/paymentService.ts

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8009/api/v1/audiobooker_proxy';

export interface CartItem {
  book_id: string;
  quantity: number;
  price_cents: number;
  credits: number;
  title: string;
}

export interface PaymentIntentResponse {
  payment_id: string;
  client_secret: string;
  payment_intent_id: string;
  amount_cents: number;
  currency: string;
  status: string;
}

export interface CheckoutSessionResponse {
  session_id: string;
  checkout_url: string;
  payment_id: string;
  amount_cents: number;
  currency: string;
}

export interface CreditsPaymentResponse {
  payment_id: string;
  order_id: string;
  credits_deducted: number;
  status: string;
  message: string;
}

export const paymentService = {
  /**
   * Get Stripe publishable key for frontend initialization
   */
  async getPublishableKey(): Promise<{ publishable_key: string; mode: string }> {
    const response = await fetch(`${API_BASE}/payment/config/publishable-key`);
    if (!response.ok) throw new Error('Failed to get publishable key');
    return response.json();
  },

  /**
   * Create a payment intent for custom payment forms
   */
  async createPaymentIntent(
    userId: string,
    items: CartItem[]
  ): Promise<PaymentIntentResponse> {
    const response = await fetch(`${API_BASE}/payment/create-payment-intent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, items }),
    });
    if (!response.ok) throw new Error('Failed to create payment intent');
    return response.json();
  },

  /**
   * Create a checkout session for Stripe hosted checkout
   */
  async createCheckoutSession(
    userId: string,
    items: CartItem[],
    customerEmail?: string
  ): Promise<CheckoutSessionResponse> {
    const response = await fetch(`${API_BASE}/payment/create-checkout-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        items,
        customer_email: customerEmail,
      }),
    });
    if (!response.ok) throw new Error('Failed to create checkout session');
    return response.json();
  },

  /**
   * Pay using account credits
   */
  async payWithCredits(
    userId: string,
    items: CartItem[],
    totalCredits: number
  ): Promise<CreditsPaymentResponse> {
    const response = await fetch(`${API_BASE}/payment/pay-with-credits`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        items,
        total_credits: totalCredits,
      }),
    });
    if (!response.ok) throw new Error('Failed to process credits payment');
    return response.json();
  },

  /**
   * Get payment status
   */
  async getPaymentStatus(paymentId: string): Promise<any> {
    const response = await fetch(`${API_BASE}/payment/payment/${paymentId}`);
    if (!response.ok) throw new Error('Failed to get payment status');
    return response.json();
  },

  /**
   * Get user's payment history
   */
  async getUserPayments(userId: string): Promise<{ payments: any[]; count: number }> {
    const response = await fetch(`${API_BASE}/payment/user/${userId}/payments`);
    if (!response.ok) throw new Error('Failed to get user payments');
    return response.json();
  },

  /**
   * Get user's order history
   */
  async getUserOrders(userId: string): Promise<{ orders: any[]; count: number }> {
    const response = await fetch(`${API_BASE}/payment/user/${userId}/orders`);
    if (!response.ok) throw new Error('Failed to get user orders');
    return response.json();
  },
};
```

### Step 3: Update Checkout Component

Update the Checkout.tsx to integrate with the payment service:

```typescript
// In Checkout.tsx payment step

import { loadStripe } from '@stripe/stripe-js';
import { Elements, PaymentElement, useStripe, useElements } from '@stripe/react-stripe-js';
import { paymentService } from '@/services/paymentService';

// Initialize Stripe outside component
let stripePromise: Promise<any> | null = null;

const getStripe = async () => {
  if (!stripePromise) {
    const { publishable_key } = await paymentService.getPublishableKey();
    stripePromise = loadStripe(publishable_key);
  }
  return stripePromise;
};

// In payment step component
const handleCardPayment = async () => {
  setIsProcessing(true);
  
  try {
    // 1. Create payment intent
    const { client_secret, payment_id } = await paymentService.createPaymentIntent(
      userId,
      cartItems.map(item => ({
        book_id: item.bookId,
        quantity: item.quantity,
        price_cents: item.priceAtAdd,
        credits: item.creditsAtAdd,
        title: item.title,
      }))
    );
    
    // 2. Get Stripe instance
    const stripe = await getStripe();
    
    // 3. Confirm payment
    const { error, paymentIntent } = await stripe.confirmPayment({
      clientSecret: client_secret,
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/checkout/success?payment_id=${payment_id}`,
      },
    });
    
    if (error) {
      setError(error.message);
    }
  } catch (err) {
    setError('Payment failed. Please try again.');
  } finally {
    setIsProcessing(false);
  }
};

const handleCreditsPayment = async () => {
  setIsProcessing(true);
  
  try {
    const result = await paymentService.payWithCredits(
      userId,
      cartItems.map(item => ({
        book_id: item.bookId,
        quantity: item.quantity,
        price_cents: item.priceAtAdd,
        credits: item.creditsAtAdd,
        title: item.title,
      })),
      totalCredits
    );
    
    // Redirect to success page
    navigate(`/checkout/success?payment_id=${result.payment_id}`);
  } catch (err) {
    setError('Credits payment failed. Please try again.');
  } finally {
    setIsProcessing(false);
  }
};
```

## Webhook Configuration

For Stripe webhooks to work, configure the webhook endpoint in Stripe Dashboard:

### Development (with Stripe CLI)

```bash
stripe listen --forward-to localhost:8004/api/v1/payment/webhook/stripe
```

### Production

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-api-domain.com/api/v1/payment/webhook/stripe`
3. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
   - `checkout.session.completed`
   - `charge.refunded`
4. Copy the signing secret to `STRIPE_WEBHOOK_SECRET`

## Testing

### Test Card Numbers

| Card Number | Behavior |
|-------------|----------|
| `4242424242424242` | Succeeds |
| `4000000000000002` | Declined |
| `4000000000009995` | Insufficient funds |
| `4000002500003155` | Requires 3D Secure |

Use any future date for expiry and any 3-digit CVC.

### Test Credits Payment

1. Ensure user has credits in auth database:
```javascript
// In MongoDB shell
db.users.updateOne(
  { email: "test@example.com" },
  { $set: { credits: 100 } }
)
```

2. Call credits payment endpoint with sufficient credits

## Error Handling

The payment service returns standard HTTP error codes:

| Code | Meaning |
|------|---------|
| 400 | Invalid request (e.g., insufficient credits) |
| 404 | Resource not found (e.g., payment not found) |
| 500 | Server error (e.g., Stripe API failure) |

Error response format:
```json
{
  "detail": "Error message"
}
```
