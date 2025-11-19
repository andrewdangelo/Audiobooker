from fastapi import (APIRouter, Request)
from app.models.schemas import (HealthResponse)
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/check_health", response_model=HealthResponse)
async def health_check(request: Request):
    """Health check endpoint"""
    main_app =  os.path.basename(os.getcwd())
    return HealthResponse(
        status="healthy",
        service=main_app,
        timestamp=datetime.utcnow(),
        version=request.app.__version__
    )