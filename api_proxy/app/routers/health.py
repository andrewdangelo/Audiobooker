"""
Health Check Router
"""

from fastapi import APIRouter
import httpx
import logging
from typing import Dict, Any

from config.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """API Gateway health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/services")
async def services_health_check() -> Dict[str, Any]:
    """Check health of all microservices"""
    services = {
        "pdf-processor": settings.PDF_PROCESSOR_URL,
        "tts-service": settings.TTS_SERVICE_URL,
        "storage-service": settings.STORAGE_SERVICE_URL,
    }
    
    results = {
        "api-gateway": "healthy",
        "services": {}
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services.items():
            try:
                response = await client.get(f"{url}/health")
                if response.status_code == 200:
                    results["services"][name] = "healthy"
                else:
                    results["services"][name] = f"unhealthy (status: {response.status_code})"
            except httpx.RequestError as e:
                results["services"][name] = f"unreachable ({str(e)})"
            except Exception as e:
                results["services"][name] = f"error ({str(e)})"
    
    # Overall status
    all_healthy = all(
        status == "healthy" 
        for status in results["services"].values()
    )
    results["overall"] = "healthy" if all_healthy else "degraded"
    
    return results
