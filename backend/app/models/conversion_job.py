"""
Conversion Job Database Model
"""

from sqlalchemy import Column, String, DateTime, Enum, Integer, Text
from sqlalchemy.sql import func
from config.database import Base
import enum


class JobStatus(str, enum.Enum):
    """Conversion job status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversionJob(Base):
    """Conversion job model for tracking PDF to audiobook conversions"""
    
    __tablename__ = "conversion_jobs"
    
    id = Column(String, primary_key=True, index=True)
    audiobook_id = Column(String, nullable=False, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED)
    
    # Progress tracking
    total_pages = Column(Integer, nullable=True)
    processed_pages = Column(Integer, default=0)
    progress_percentage = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<ConversionJob {self.id} - {self.status}>"
