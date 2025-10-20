"""
Audiobook Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AudiobookStatus(str, Enum):
    """Audiobook status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudiobookBase(BaseModel):
    """Base audiobook schema"""
    title: str = Field(..., min_length=1, max_length=255)


class AudiobookCreate(AudiobookBase):
    """Schema for creating an audiobook"""
    original_file_name: str
    file_size: int


class AudiobookUpdate(BaseModel):
    """Schema for updating an audiobook"""
    title: Optional[str] = None
    status: Optional[AudiobookStatus] = None


class AudiobookResponse(AudiobookBase):
    """Schema for audiobook response"""
    id: str
    original_file_name: str
    file_size: int
    duration: Optional[float] = None
    status: AudiobookStatus
    audio_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class AudiobookListResponse(BaseModel):
    """Schema for audiobook list response"""
    items: list[AudiobookResponse]
    total: int
    page: int
    page_size: int
