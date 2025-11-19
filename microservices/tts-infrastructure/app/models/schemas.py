"""
Pydantic Models and Schemas... reference docs page for fast api

Request/Response models for API endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class HealthResponse(BaseModel):
    """Health check response"""
    
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
