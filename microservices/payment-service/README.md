# Payment Microservice

FastAPI-based microservice for payment processing using Stripe API with MongoDB persistence.

## Features

- **Stripe Payment Intent** - For custom payment forms using Stripe Elements
- **Stripe Checkout Session** - For Stripe's hosted checkout page
- **Credits Payment** - Pay using user account credits (non-Stripe)
- **Webhook Handling** - Process Stripe payment events
- **Refunds** - Full and partial refund support
- **Order Management** - Automatic order creation on successful payment
- **Sandbox Mode** - Automatically uses test mode in development

## Architecture

```
Frontend → API Proxy → Payment Service → Stripe API
                              ↓
                          MongoDB
                              ↓
                    Auth Service (user lookup)
```

## Quick Start

### 1. Install Dependencies

```bash
cd microservices/payment-service
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and configure:

```bash
cp .env.example .env
```

**Required Settings:**

```env
# Stripe Test Keys (from https://dashboard.stripe.com/test/apikeys)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=audiobooker_payment

# Auth MongoDB (for user lookups)
AUTH_MONGODB_URL=mongodb://localhost:27017
AUTH_MONGODB_DB_NAME=audiobooker_auth
```

### 3. Start the Service

```bash
python main.py
```

Service runs on `http://localhost:8004`

### 4. Test with Stripe CLI (for webhooks)

```bash
# Install Stripe CLI: https://stripe.com/docs/stripe-cli
stripe listen --forward-to localhost:8004/api/v1/payment/webhook/stripe
```

## API Endpoints

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/payment/config/publishable-key` | Get Stripe publishable key for frontend |

### Payment Intent (Custom Forms)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payment/create-payment-intent` | Create a Stripe Payment Intent |
| POST | `/api/v1/payment/confirm-payment` | Confirm a payment (server-side) |

### Checkout Session (Hosted Checkout)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payment/create-checkout-session` | Create a Stripe Checkout Session |
| GET | `/api/v1/payment/checkout-session/{session_id}` | Get checkout session status |

### Credits Payment

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payment/pay-with-credits` | Pay using account credits |

### Payment Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/payment/payment/{payment_id}` | Get payment status |
| GET | `/api/v1/payment/user/{user_id}/payments` | Get user's payment history |
| GET | `/api/v1/payment/user/{user_id}/orders` | Get user's order history |

### Refunds

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payment/refund` | Create a refund |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/payment/webhook/stripe` | Stripe webhook endpoint |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/payment/health/` | Health check |
| GET | `/api/v1/payment/health/live` | Liveness probe |
| GET | `/api/v1/payment/health/ready` | Readiness probe |

## Frontend Integration

### Option 1: Stripe Elements (Custom Form)

```typescript
// 1. Get publishable key
const { publishable_key } = await fetch('/api/v1/payment/config/publishable-key').then(r => r.json())

// 2. Initialize Stripe
const stripe = await loadStripe(publishable_key)

// 3. Create Payment Intent
const { client_secret } = await fetch('/api/v1/payment/create-payment-intent', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user_123',
    items: [
      { book_id: 'book_1', quantity: 1, price_cents: 999, credits: 1, title: 'Book Title' }
    ]
  })
}).then(r => r.json())

// 4. Confirm payment with Stripe Elements
const { error, paymentIntent } = await stripe.confirmPayment({
  elements,
  clientSecret: client_secret,
  confirmParams: { return_url: 'http://localhost:5173/checkout/success' }
})
```

### Option 2: Stripe Checkout (Hosted Page)

```typescript
// 1. Create Checkout Session
const { checkout_url } = await fetch('/api/v1/payment/create-checkout-session', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user_123',
    items: [
      { book_id: 'book_1', quantity: 1, price_cents: 999, credits: 1, title: 'Book Title' }
    ],
    customer_email: 'user@example.com'
  })
}).then(r => r.json())

// 2. Redirect to Stripe Checkout
window.location.href = checkout_url
```

### Option 3: Credits Payment

```typescript
const result = await fetch('/api/v1/payment/pay-with-credits', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    user_id: 'user_123',
    items: [{ book_id: 'book_1', quantity: 1, price_cents: 999, credits: 1, title: 'Book Title' }],
    total_credits: 1
  })
}).then(r => r.json())
```

## Test Card Numbers

When using Stripe test mode:

| Card Number | Description |
|-------------|-------------|
| `4242424242424242` | Successful payment |
| `4000000000000002` | Declined card |
| `4000000000009995` | Insufficient funds |
| `4000002500003155` | Requires 3D Secure |

Use any future expiry date and any 3-digit CVC.

## Sandbox vs Production

The service automatically detects mode based on Stripe key prefix:

- `sk_test_*` → Sandbox/Test mode
- `sk_live_*` → Production mode

**Important:** Never use live keys in development!

## MongoDB Collections

### payments
Stores payment records with Stripe intent/session IDs.

### orders
Created automatically when payment succeeds.

### webhook_events
Stores processed webhook events for idempotency.

### subscriptions
Reserved for future subscription support.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | development | Environment mode |
| `PORT` | 8004 | Service port |
| `MONGODB_URL` | mongodb://localhost:27017 | Payment DB URL |
| `MONGODB_DB_NAME` | audiobooker_payment | Payment DB name |
| `AUTH_MONGODB_URL` | mongodb://localhost:27017 | Auth DB URL |
| `AUTH_MONGODB_DB_NAME` | audiobooker_auth | Auth DB name |
| `STRIPE_SECRET_KEY` | - | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | - | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | - | Webhook signing secret |
| `PAYMENT_SUCCESS_URL` | http://localhost:5173/checkout/success | Success redirect |
| `PAYMENT_CANCEL_URL` | http://localhost:5173/checkout/cancel | Cancel redirect |

## API Proxy Integration

The service is accessible through the API proxy at:

```
http://localhost:8009/api/v1/audiobooker_proxy/payment/*
```

Example:
```bash
curl http://localhost:8009/api/v1/audiobooker_proxy/payment/health/
```

## Docker

```bash
docker build -t audiobooker-payment-service .
docker run -p 8004:8004 --env-file .env audiobooker-payment-service
```

## Troubleshooting

### Stripe webhook signature invalid
- Ensure `STRIPE_WEBHOOK_SECRET` is set correctly
- Use Stripe CLI for local testing: `stripe listen --forward-to localhost:8004/api/v1/payment/webhook/stripe`

### MongoDB connection failed
- Check MongoDB is running
- Verify `MONGODB_URL` is correct

### User not found for credits payment
- Ensure auth service MongoDB is accessible
- Verify `AUTH_MONGODB_URL` and `AUTH_MONGODB_DB_NAME`
