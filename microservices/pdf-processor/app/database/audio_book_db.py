"""
Audiobook Service
#TODO Can implement new db tables later on
"""

from sqlalchemy.orm import Session
from typing import Dict, Any


class AudiobookDBService:
    """Generic DB service for audiobook-related models"""

    def __init__(self, db: Session, model):
        self.db = db
        self.model = model

    def create(self, data: Dict[str, Any]):
        instance = self.model(**data)
        try:
            self.db.add(instance)
            self.db.commit()
            self.db.refresh(instance)
        except Exception as e:
            # In the case you need to update row of same r2_key
            self.db.rollback()
            item_id = data.get("r2_key")
            if not item_id:
                raise ValueError("r2_key is required for update on conflict.")
            else:
                existing = self.db.query(self.model).filter(self.model.r2_key == item_id).first()
                
                for key, value in data.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
                
                self.db.commit()
                self.db.refresh(existing)
        
        return instance

    def get_by_id(self, item_id: str):
        return self.db.query(self.model).filter(self.model.r2_key == item_id).first()

    def get_all(self, skip=0, limit=20):
        return self.db.query(self.model).offset(skip).limit(limit).all()

    def count(self):
        return self.db.query(self.model).count()

    def update(self, item_id: str, update_data: Dict[str, Any]):
        instance = self.get_by_id(item_id)
        if not instance:
            return None

        for key, value in update_data.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)

        self.db.commit()
        self.db.refresh(instance)
        return instance

    def delete(self, item_id: str) -> bool:
        instance = self.get_by_id(item_id)
        if not instance:
            return False

        self.db.delete(instance)
        self.db.commit()
        return True

