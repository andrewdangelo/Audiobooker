"""
- AI Microservice - 
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import (Dict, Any)
import uvicorn
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path
import json

import aioboto3
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.routers import ai_generation, voice_library, health
from app.services.voice_library import VoiceLibraryManager

BASE_DIR = Path(__file__).resolve().parent

__version__ = settings.TEST_VERSION
__author__ = "Matt"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    logger.info("🚀 LIFESPAN STARTUP RUNNING")
    
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    collection = mongo_client["audiobooker_backend_db"]["voice_library"]
 
    r2_session = aioboto3.Session()
    r2_config = {
        "account_id": settings.R2_ACCOUNT_ID,
        "access_key": settings.R2_ACCESS_KEY_ID,
        "secret_key": settings.R2_SECRET_ACCESS_KEY,
        "bucket":     settings.R2_BUCKET_NAME,
    }
 
    app.state.voice_manager = VoiceLibraryManager(collection, r2_session, r2_config)
    logger.info("VoiceLibraryManager initialised")
 
    yield
 
    # --- shutdown ---
    mongo_client.close()
    logger.info("Mongo connection closed")

# Initialize FastAPI app
app = FastAPI(
    title="AI Infrastructure Microservice",
    description="Microservice For AI Tasks",
    version=__version__,
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

# Apply essential info to app object
app.__version__ = __version__

app.include_router(
    health.router, 
    prefix=f"{settings.API_V1_PREFIX}/health", 
    tags=["-HEALTH-"]
)

app.include_router(
    ai_generation.router, 
    prefix=f"{settings.API_V1_PREFIX}/ai",
    tags=["AI Generation"]
)

app.include_router(
    voice_library.router, 
    prefix=f"{settings.API_V1_PREFIX}/ai",
    tags=["Voice Library"]
)

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "service": "AI Infrastructure Microservice",
        "status": "running",
        "docs": "Please visit Docs page ---> host_addr/docs :)"
    }

if __name__ == "__main__":
    # Run the application based on environment
    uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "development", log_level=settings.LOG_LEVEL.lower())
    # uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "production", log_level=settings.LOG_LEVEL.lower())