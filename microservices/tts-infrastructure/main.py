"""
- PDF Processing Microservice - 

FastAPI-based microservice for TTS Tasks. 
Full Capabilities: DB Utilization using Postgres: Usage of different TTS Engines

"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import (Dict, Any)
import uvicorn
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import asyncio

from app.core.config_settings import settings
from app.core.redis_manager import redis_manager
from app.core.logging_config import setup_logging
from app.routers import (health, tts, audio_stitching)
from app.services import audio_stitcher

__version__ = settings.TEST_VERSION
__author__ = "babyboy"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="TTS Infrastructure Microservice",
    description="Microservice For TTS Infrastructure Tasks",
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

# Apply essential info to app object
app.__version__ = __version__

app.include_router(
    health.router, 
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["-HEALTH-"]
)

app.include_router(
    tts.router, 
    prefix=f"{settings.API_V1_PREFIX}/tts_processor",
    tags=["-TTS_SERVICE-"]
)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # Startup: Start the cleanup task
#     if audio_stitching.audio_stitcher._cleanup_task is None:
#         audio_stitching.audio_stitcher._cleanup_task = asyncio.create_task(
#             audio_stitching.audio_stitcher._cleanup_old_jobs()
#         )
#     yield
#     # Shutdown: Cancel the cleanup task
#     if audio_stitching.audio_stitcher._cleanup_task:
#         audio_stitching.audio_stitcher._cleanup_task.cancel()
        
app.include_router(
    audio_stitching.router, 
    prefix=f"{settings.API_V1_PREFIX}/audio-stitch",
    tags=["-Audio Stitching-"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        #TODO remove this way to start redis server and dedicate a vm for redis server or microservice. SUPER TEMPORARY FIX
        import subprocess as sp
        sp.run('wsl -d Ubuntu bash -c "sudo service redis-server start"', shell=True)
        await redis_manager.connect()        
        stitcher = audio_stitcher.AudioStitcher()
        await stitcher.initialize()
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise e
    
    logger.info("Starting TTS Microservice")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Started redis connection: {settings.REDIS_HOST}:{settings.REDIS_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown TODO Can apply cleanup tasks here and retry mechanisms"""
    try:
        stitcher = audio_stitcher.AudioStitcher()
        await stitcher.close()
        await redis_manager.disconnect()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise e
    
    logger.info("Shutting down TTS Microservice")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "service": "TTS Infrastructure Microservice",
        "status": "running",
        "docs": "Please visit Docs page ---> host_addr/docs :)"
    }

if __name__ == "__main__":
    # Run the application based on environment
    uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "development", log_level=settings.LOG_LEVEL.lower())
    # uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "production", log_level=settings.LOG_LEVEL.lower())