"""
Payment Microservice - Main Entry Point

FastAPI-based microservice for payment processing using Stripe.
Supports both sandbox (test) mode and production mode.
Uses MongoDB for payment and order persistence.
"""

__author__ = "Payment Service Team"
__version__ = "1.0.0"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.database.mongodb import MongoDB
from app.routers import health
from app.routers.payment import router as payment_router
from app.routers.webhook import router as webhook_router
from app.routers.subscription import router as subscription_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Payment Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Stripe Mode: {'SANDBOX/TEST' if settings.is_sandbox_mode else 'LIVE/PRODUCTION'}")
    
    try:
        await MongoDB.connect()
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    
    # Validate Stripe configuration
    stripe_key = settings.STRIPE_SECRET_KEY
    if not stripe_key:
        logger.warning("[WARNING] Stripe secret key not configured - payments will fail!")
        logger.warning(f"  Check that .env file exists at: {settings.model_config.get('env_file', 'unknown')}")
    elif not settings.validate_stripe_keys():
        logger.warning("[WARNING] Stripe key mismatch - check your configuration!")
    else:
        # Mask the key for logging
        masked_key = stripe_key[:12] + "..." + stripe_key[-4:] if len(stripe_key) > 20 else "***"
        logger.info(f"[OK] Stripe configuration validated (key: {masked_key})")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Payment Service...")
    await MongoDB.disconnect()


# Initialize FastAPI app
app = FastAPI(
    title="Audiobooker Payment Service",
    description="Microservice for payment processing with Stripe integration",
    version=settings.TEST_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Apply version to app
app.__version__ = settings.TEST_VERSION


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    stripe_mode = "sandbox" if settings.is_sandbox_mode else "live"
    return {
        "service": "Audiobooker Payment Service",
        "version": settings.TEST_VERSION,
        "status": "running",
        "stripe_mode": stripe_mode
    }


# Include routers
app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["-HEALTH-"]
)

app.include_router(
    payment_router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["-PAYMENT-"]
)

app.include_router(
    webhook_router,
    prefix=f"{settings.API_V1_PREFIX}/webhook",
    tags=["-WEBHOOK-"]
)

app.include_router(
    subscription_router,
    prefix=f"{settings.API_V1_PREFIX}/subscription",
    tags=["-SUBSCRIPTION-"]
)


if __name__ == "__main__":
    logger.info(f"Starting Payment Service on port {settings.PORT}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
