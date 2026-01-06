"""
API Proxy - Micro 
"""
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.core.redis_manager import redis_manager
from app.core.rate_limiter import limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.routers import proxy_router
from app.services.queue_worker import start_queue_workers, stop_queue_workers

# Setup logging service
setup_logging()
logger = logging.getLogger(__name__)

# ==================== APP INITIALIZATION ====================

app = FastAPI(
    title="API Proxy For Audiobooker Microservices",
    description="Rate limiting and Request queueing",
    version="0.0.1"
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Include routers
app.include_router(proxy_router.router)

# ==================== LIFECYCLE EVENTS ====================

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting API Proxy...")
    
    # Connect to Redis
    await redis_manager._ensure_connection()
    logger.info("Redis connected")
    
    # Start queue workers
    await start_queue_workers()
    
    logger.info("Queue workers started")
    logger.info("API Proxy ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down API Proxy...")
    
    # Stop queue workers
    await stop_queue_workers()
    
    # Disconnect Redis
    await redis_manager.disconnect()
    
    logger.info("API Proxy shut down")


# ==================== GLOBAL ERROR HANDLER ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Catch-all exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# ==================== RUN ====================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.PORT, reload=settings.ENVIRONMENT == "develfopment", log_level=settings.LOG_LEVEL.lower())