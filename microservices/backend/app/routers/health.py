"""
API Health Endpoint
"""

__author__ = "Mohammad Saifan"

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
    main_app =  f"{os.path.basename(os.getcwd())} Microservice"
    
    now = datetime.now()
    date_str = now.strftime("%m-%d-%Y")
    time_str = now.strftime("%I:%M %p")
    return HealthResponse(
        status="healthy",
        service=main_app,
        timestamp=f"{date_str} at {time_str}",
        version=request.app.__version__
    )