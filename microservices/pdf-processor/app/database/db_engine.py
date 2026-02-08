"""
MongoDB Audiobook Service
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MongoDBService:
    """Generic MongoDB service for audiobook collections"""

    def __init__(self, db, collection_name: str):
        """Initialize MongoDB service"""
        self.db = db
        self.collection_name = collection_name
        self.collection = db[collection_name]

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document, or update if r2_key exists"""
        try:
            now = datetime.utcnow()
            data['created_at'] = now
            data['updated_at'] = now
            result = self.collection.insert_one(data)
            data['_id'] = result.inserted_id
            return data
        except Exception as e:
            # Handle duplicate r2_key by updating
            logger.warning(f"Document creation conflict, attempting update: {e}")
            item_id = data.get("r2_key")
            if not item_id:
                raise ValueError("r2_key is required for update on conflict")
            existing = self.collection.find_one({"r2_key": item_id})
            if existing:
                data['updated_at'] = datetime.utcnow()
                self.collection.update_one({"r2_key": item_id}, {"$set": data})
                return self.collection.find_one({"r2_key": item_id})
            raise

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get document by r2_key"""
        try:
            return self.collection.find_one({"r2_key": item_id})
        except Exception as e:
            logger.error(f"Error fetching document: {e}")
            return None

    def get_all(self, skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all documents with pagination"""
        try:
            cursor = self.collection.find().skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error fetching documents: {e}")
            return []

    def count(self) -> int:
        """Count total documents"""
        try:
            return self.collection.count_documents({})
        except Exception as e:
            logger.error(f"Error counting documents: {e}")
            return 0

    def update(self, item_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a document"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = self.collection.find_one_and_update({"r2_key": item_id}, {"$set": update_data}, return_document=True)
            return result
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise e

    def delete(self, item_id: str) -> bool:
        """Delete a document"""
        try:
            result = self.collection.delete_one({"r2_key": item_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            return False