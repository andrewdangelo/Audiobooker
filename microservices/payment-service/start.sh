#!/bin/bash
# Start script for Payment Service

echo "==================================="
echo "  Audiobooker Payment Service"
echo "==================================="

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Copy .env.example to .env and configure your settings"
    echo "   cp .env.example .env"
    exit 1
fi

# Check for Stripe keys
source .env 2>/dev/null
if [ -z "$STRIPE_SECRET_KEY" ] || [ "$STRIPE_SECRET_KEY" = "sk_test_your_test_secret_key_here" ]; then
    echo "⚠️  Warning: Stripe secret key not configured!"
    echo "   Get your test keys from: https://dashboard.stripe.com/test/apikeys"
fi

# Create logs directory
mkdir -p logs

echo ""
echo "Starting Payment Service..."
echo "Docs: http://localhost:${PORT:-8004}/docs"
echo ""

# Run the service
python main.py
