"""
TTS Infrastructure Microservice
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

import arq
from arq.connections import RedisSettings

from app.core.config_settings import settings
from app.core.redis_manager import redis_manager
from app.core.logging_config import setup_logging
from app.routers import health, tts, audio_stitching, book_generation
from app.services import audio_stitcher

__version__ = settings.TEST_VERSION
__author__ = "babyboy"

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TTS Infrastructure Microservice",
    description="Microservice For TTS Infrastructure Tasks",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

app.include_router(
    audio_stitching.router,
    prefix=f"{settings.API_V1_PREFIX}/audio-stitch",
    tags=["-Audio Stitching-"]
)

app.include_router(
    book_generation.router,
    prefix=f"{settings.API_V1_PREFIX}/book-generation",
    tags=["-Book Generation-"]
)


@app.on_event("startup")
async def startup_event():
    try:
        # Matt - I have this running as a Windows Service
        # import subprocess as sp
        # sp.run('wsl -d Ubuntu-22.04 bash -c "sudo service redis-server start"', shell=True)
        await redis_manager.connect()
        stitcher = audio_stitcher.AudioStitcher()
        await stitcher.initialize()

        # Create ARQ Redis pool and attach to app.state so the router
        # can access it via req.app.state.arq_pool.
        # Uses the same Redis instance as everything else.
        app.state.arq_pool = await arq.create_pool(
            RedisSettings(
                # host=settings.REDIS_HOST,
                host='127.0.0.1',
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                database=settings.REDIS_DB,
            )
        )
        logger.info("ARQ pool connected")

    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise e

    logger.info("Starting TTS Microservice")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"AI Service: {settings.AI_SERVICE_BASE_URL}")


@app.on_event("shutdown")
async def shutdown_event():
    try:
        await app.state.arq_pool.close()
        stitcher = audio_stitcher.AudioStitcher()
        await stitcher.close()
        await redis_manager.disconnect()
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        raise e

    logger.info("Shutting down TTS Microservice")


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "TTS Infrastructure Microservice",
        "status": "running",
        "docs": "Please visit Docs page ---> host_addr/docs :)"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower()
    )