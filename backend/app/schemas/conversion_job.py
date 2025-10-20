"""
Conversion Job Pydantic Schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    """Job status enum"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionJobBase(BaseModel):
    """Base conversion job schema"""
    audiobook_id: str


class ConversionJobCreate(ConversionJobBase):
    """Schema for creating a conversion job"""
    pass


class ConversionJobResponse(ConversionJobBase):
    """Schema for conversion job response"""
    id: str
    status: JobStatus
    total_pages: Optional[int] = None
    processed_pages: int
    progress_percentage: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
