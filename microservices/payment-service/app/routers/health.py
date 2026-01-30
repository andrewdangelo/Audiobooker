"""
Health Check Router
"""

from fastapi import APIRouter
from app.core.config_settings import settings
from app.models.schemas import HealthCheckResponse

router = APIRouter()


@router.get("/", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    stripe_mode = "sandbox" if settings.is_sandbox_mode else "live"
    return HealthCheckResponse(
        status="healthy",
        version=settings.TEST_VERSION,
        service="Payment Service",
        stripe_mode=stripe_mode
    )


@router.get("/live", response_model=dict, tags=["Health"])
async def liveness_check():
    """Liveness check endpoint"""
    return {"status": "alive"}


@router.get("/ready", response_model=dict, tags=["Health"])
async def readiness_check():
    """Readiness check endpoint"""
    return {"status": "ready"}
