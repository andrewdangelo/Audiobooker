"""
Audiobook Service
#TODO Can implement new db tables later on
"""

from sqlalchemy.orm import Session
from app.models.audiobook import Audiobook
from typing import List, Optional, Dict, Any


class AudiobookDBService:
    """Service for managing audiobooks"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, audiobook_data: Dict[str, Any]) -> Audiobook:
        """Create a new audiobook"""
        audiobook = Audiobook(**audiobook_data)
        self.db.add(audiobook)
        self.db.commit()
        self.db.refresh(audiobook)
        return audiobook
    
    def get_by_id(self, audiobook_id: str) -> Optional[Audiobook]:
        """Get audiobook by ID"""
        return self.db.query(Audiobook).filter(Audiobook.id == audiobook_id).first()
    
    def get_all(self, skip: int = 0, limit: int = 20) -> List[Audiobook]:
        """Get all audiobooks with pagination"""
        return self.db.query(Audiobook).offset(skip).limit(limit).all()
    
    def count(self) -> int:
        """Get total count of audiobooks"""
        return self.db.query(Audiobook).count()
    
    def update(self, audiobook_id: str, update_data: Dict[str, Any]) -> Optional[Audiobook]:
        """Update an audiobook"""
        audiobook = self.get_by_id(audiobook_id)
        if not audiobook:
            return None
        
        for key, value in update_data.items():
            if hasattr(audiobook, key) and value is not None:
                setattr(audiobook, key, value)
        
        self.db.commit()
        self.db.refresh(audiobook)
        return audiobook
    
    def delete(self, audiobook_id: str) -> bool:
        """Delete an audiobook"""
        audiobook = self.get_by_id(audiobook_id)
        if not audiobook:
            return False
        
        self.db.delete(audiobook)
        self.db.commit()
        return True
