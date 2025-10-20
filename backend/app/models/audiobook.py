"""
Audiobook Database Model
"""

from sqlalchemy import Column, String, Integer, DateTime, Enum, Float
from sqlalchemy.sql import func
from config.database import Base
import enum


class AudiobookStatus(str, enum.Enum):
    """Audiobook processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Audiobook(Base):
    """Audiobook model"""
    
    __tablename__ = "audiobooks"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    original_file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    duration = Column(Float, nullable=True)  # Duration in seconds
    status = Column(Enum(AudiobookStatus), default=AudiobookStatus.PENDING)
    
    # Storage paths
    pdf_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Audiobook {self.title}>"
