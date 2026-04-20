"""
Pydantic Models and Schemas

Request/Response models for API endpoints.
"""

from pydantic import BaseModel, Field

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")
