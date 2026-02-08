"""
MongoDB Collection Schemas for PDF Processor
"""
__author__ = "Mohammad Saifan"

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class Collections:
    """Collection names"""
    AUDIOBOOKS = "audiobooks"
    PROCESSED_AUDIOBOOKS = "processed_audiobooks"


class AudiobookStatus(str, Enum):
    """Audiobook processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudiobookModel(BaseModel):
    """Audiobook document model"""
    r2_key: str
    user_id: str
    title: str
    status: AudiobookStatus = AudiobookStatus.PENDING
    pdf_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProcessedAudiobookModel(BaseModel):
    """Processed Audiobook document model"""
    r2_key: str
    user_id: str
    title: str
    status: AudiobookStatus = AudiobookStatus.PENDING
    pdf_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)