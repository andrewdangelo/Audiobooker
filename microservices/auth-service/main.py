"""
Authentication Microservice - Main Entry Point

FastAPI-based microservice for user authentication and account management.
Supports local authentication and Google OAuth integration.
Uses MongoDB for data persistence.
"""

__author__ = "Auth Service Team"
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
from app.routers.auth_mongo import router as auth_router
from app.routers.accounts_mongo import router as accounts_router

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Auth Service...")
    try:
        await MongoDB.connect()
        logger.info("MongoDB connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auth Service...")
    await MongoDB.disconnect()


# Initialize FastAPI app
app = FastAPI(
    title="Audiobooker Authentication Service",
    description="Microservice for user authentication, account management, and Google OAuth integration",
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


# Include routers
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Audiobooker Auth Service",
        "version": settings.TEST_VERSION,
        "status": "running"
    }


app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["-HEALTH-"]
)

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["-AUTH-"]
)

app.include_router(
    accounts_router,
    prefix=f"{settings.API_V1_PREFIX}/accounts",
    tags=["-ACCOUNTS-"]
)


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info(f"Auth Service started on port {settings.PORT}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Google OAuth enabled: {bool(settings.GOOGLE_CLIENT_ID)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("Auth Service shutdown")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
