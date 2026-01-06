"""
- PDF Processing Microservice - 

FastAPI-based microservice for processing PDFs and TODO Ebooks .. from R2 storage. 
Full Capabilities include text extraction, chunking, and formatting and DB Utilization using Postgres

"""
__author__ = "Mohammad Saifan"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from app.core.config_settings import settings
from app.core.logging_config import setup_logging
from app.routers import (health, pdf_postgres_database, processed_json_postgres_database, pdf_processor, r2_processor)
from app.core.redis_manager import redis_manager

__version__ = settings.TEST_VERSION

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Audiobooker PDF Processing Service",
    description="Microservice for processing PDFs from R2 storage. Postgress audibook database utilization. Cloudflare R2 integration.",
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

# Include health router
app.include_router(
    health.router, 
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["-HEALTH-"]
)

# Include pdf_processing router
app.include_router(
    pdf_processor.router,
    prefix=f"{settings.API_V1_PREFIX}/pdf_processor",
    tags=["-PDF PROCESSOR-"]
)

# Include pdf_postgres_database router
app.include_router(
    pdf_postgres_database.router,
    prefix=f"{settings.API_V1_PREFIX}/pdf_postgres_database",
    tags=["-PDF POSTGRES AUDIOBOOK DATABASE-"]
)

# Include r2_database router
app.include_router(
    processed_json_postgres_database.router,
    prefix=f"{settings.API_V1_PREFIX}/processed_json_postgres_database",
    tags=["-PROCESSED JSON POSTGRES AUDIOBOOK DATABASE-"]
)

# Include r2_processor router
app.include_router(
    r2_processor.router,
    prefix=f"{settings.API_V1_PREFIX}/r2_processor",
    tags=["-Cloudflare R2 Service-"]
)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    # try:
    #     #TODO remove this way to start redis server and dedicate a vm for redis server or microservice. SUPER TEMPORARY FIX
    #     import subprocess as sp
    #     sp.run('wsl -d Ubuntu bash -c "sudo service redis-server start"', shell=True, capture_output=True)
    #     await redis_manager.connect()    
    # except Exception as e:
    #     logger.error(f"Startup failed: {str(e)}", exc_info=True)
    #     raise e
    
    logger.info("Starting PDF Processing Microservice")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"R2 Bucket: {settings.R2_BUCKET_NAME}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown TODO Can apply cleanup tasks here and retry mechanisms"""
    # try:
    #     await redis_manager.disconnect()
    # except Exception as e:
    #     logger.error(f"Shutdown failed: {str(e)}", exc_info=True)
    #     raise e
    
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
    # uvicorn.run("main:app", host="127.0.0.1", port=settings.PORT, reload=settings.ENVIRONMENT == "production", log_level=settings.LOG_LEVEL.lower())