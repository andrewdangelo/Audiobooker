"""
- PDF Processing Microservice - 

FastAPI-based microservice for processing PDFs and TODO Ebooks .. from R2 storage. 
Full Capabilities include text extraction, chunking, and formatting and DB Utilization using Postgres

"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import (Dict, Any)
import uvicorn
import logging
from datetime import datetime

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.routers import (health, pdf_processor)

__version__ = settings.TEST_VERSION
__author__ = "babyboy"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Audiobooker PDF Processing Service",
    description="Microservice for processing PDFs/Ebooks from R2 storage",
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
    tags=["HEALTH"]
)
app.include_router(
    pdf_processor.router,
    prefix=f"{settings.API_V1_PREFIX}/pdf_processor",
    tags=["PDF PROCESSOR"]
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting PDF Processing Microservice")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"R2 Bucket: {settings.R2_BUCKET_NAME}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown TODO Can apply cleanup tasks here and retry mechanisms"""
    logger.info("Shutting down PDF Processing Microservice")


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint redirect to docs"""
    return {
        "service": "PDF Processor Microservice",
        "status": "running",
        "docs": "Please visit Docs page ---> host_addr/docs :)"
    }

if __name__ == "__main__":
    # Run the application based on environment
    uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "development", log_level=settings.LOG_LEVEL.lower())