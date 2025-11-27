"""
API Proxy - FastAPI Application Entry Point

This is the main API Gateway that bridges the frontend applications (Web UI, Mobile UI)
with the internal microservices (TTS, PDF Processing, Backend, Auth) and external APIs
(Gutenberg, ElevenLabs).

Architecture:
    Frontend APPs (Web UI, Mobile UI)
          ↓
    API Proxy (FastAPI Gateway)
          ↓
    ├── Internal Microservices (TTS, PDF Processing, Backend, Auth)
    ├── Data Storage (PostgreSQL, CloudFlare R2)
    └── External APIs (Gutenberg, ElevenLabs)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import logging
import time
from contextlib import asynccontextmanager

from config.settings import settings
from app.routers import health

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    logger.info(f"API Documentation available at: /docs")
    yield
    # Shutdown
    logger.info("Shutting down API Gateway")


# Create FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    description="API Gateway bridging frontend applications with microservices",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their processing time"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request details
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Time: {process_time:.3f}s"
    )
    
    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Include routers
app.include_router(health.router, tags=["Health"])
# Add more routers here as you create them
# app.include_router(
#     pdf.router,
#     prefix=f"{settings.API_V1_PREFIX}/pdf",
#     tags=["PDF Processing"]
# )


@app.get("/")
async def root():
    """
    Root endpoint - API Gateway information
    
    Returns basic information about the API Gateway including version,
    environment, and available documentation links.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
