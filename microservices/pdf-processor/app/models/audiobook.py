"""
Audiobook Database Model
"""
__author__ = "Mohammad Saifan"

from sqlalchemy import Column, String, Integer, DateTime, Enum, Float
from sqlalchemy.sql import func
from app.database.database import Base
import enum


class AudiobookStatus(str, enum.Enum):
    """Audiobook processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Audiobook(Base):
    """Audiobook model"""
    
    __tablename__ = "Audiobooks"
    
    r2_key = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(Enum(AudiobookStatus), default=AudiobookStatus.PENDING)    
    pdf_path = Column(String, nullable=True)

    
    def __repr__(self):
        return f"<Audiobook {self.title}>"

class Processed_Audiobook(Base):
    """Processed_Audiobook model"""
    
    __tablename__ = "Processed_Audiobooks"
    
    r2_key = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    status = Column(Enum(AudiobookStatus), default=AudiobookStatus.PENDING)    
    pdf_path = Column(String, nullable=True)

    
    def __repr__(self):
        return f"<Processed_Audiobook {self.title}>"
