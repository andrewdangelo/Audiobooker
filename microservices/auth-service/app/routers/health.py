"""
Health Check Router
"""

from fastapi import APIRouter, HTTPException
from app.core.config_settings import settings
from app.models.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        version=settings.TEST_VERSION,
        service="Auth Service"
    )


@router.get("/live", response_model=dict, tags=["Health"])
async def liveness_check():
    """Liveness check endpoint"""
    return {"status": "alive"}


@router.get("/ready", response_model=dict, tags=["Health"])
async def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready"}
