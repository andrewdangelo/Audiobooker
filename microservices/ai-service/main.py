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

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.routers import ai_generation

BASE_DIR = Path(__file__).resolve().parent

__version__ = settings.TEST_VERSION
__author__ = "Matt"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     if settings.ENVIRONMENT == "development":
#         json_path = BASE_DIR / "app" / "data" / "ai_defaults.json"
#         with open(json_path, "r") as f:
#             app.state.seed_data = json.load(f)
#         logger.info(f"AI Model Defaults loaded")
#     else:
#         app.state.seed_data = []
#         logger.info("Skipping AI Model Defaults")
#     yield

# Initialize FastAPI app
app = FastAPI(
    title="AI Infrastructure Microservice",
    description="Microservice For AI Tasks",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
    # lifespan=lifespan
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
    ai_generation.router, 
    prefix=f"{settings.API_V1_PREFIX}/ai",
    tags=["-AI Generation-"]
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