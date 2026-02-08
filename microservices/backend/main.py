"""
Backend API Microservice

FastAPI-based microservice for managing users, books, library, and store.
Handles all backend operations for the application.
"""

__author__ = "Mohammad Saifan"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.routers import (
    health, 
    users, 
    books, 
    cart, 
    publishing, 
    payments, 
    permissions, 
    playback, 
    search, 
    notifications, 
    analytics, 
    admin
)
from app.core.redis_manager import redis_manager

__version__ = settings.TEST_VERSION

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Backend API Service",
    description="Microservice for managing users, books, library, and store operations.",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.__version__ = __version__

# Include health router
app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["Health"]
)

# Include users router
app.include_router(
    users.router,
    prefix=settings.API_V1_PREFIX,
    tags=["User Management"]
)

# Include books router
app.include_router(
    books.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Books & Store"]
)

# Include cart router
app.include_router(
    cart.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Cart & Checkout"]
)

# Include publishing router
app.include_router(
    publishing.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Publishing & Listings"]
)

# Include payments router
app.include_router(
    payments.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Payments & Subscriptions"]
)

# Include permissions router
app.include_router(
    permissions.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Permissions & Access Control"]
)

# Include playback router
app.include_router(
    playback.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Playback & Progress"]
)

# Include search router
app.include_router(
    search.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Search & Discovery"]
)

# Include notifications router
app.include_router(
    notifications.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Notifications"]
)

# Include analytics router
# app.include_router(
#     analytics.router,
#     prefix=settings.API_V1_PREFIX,
#     tags=["Analytics"]
# )

# Include admin router
app.include_router(
    admin.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Admin"]
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting Backend API Microservice")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Database: {settings.DATABASE_URL}")
    
    # Optionally connect to Redis if needed
    # try:
    #     await redis_manager.connect()
    # except Exception as e:
    #     logger.warning(f"Redis connection failed: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Backend API Microservice")
    
    # Optionally disconnect Redis
    # try:
    #     await redis_manager.disconnect()
    # except Exception as e:
    #     logger.error(f"Redis disconnect failed: {str(e)}")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "service": "Backend API Microservice",
        "status": "running",
        "version": __version__,
        "docs": f"Visit /docs for API documentation BUBBA"
    }


if __name__ == "__main__":
    # Run the application based on environment
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower()
    )