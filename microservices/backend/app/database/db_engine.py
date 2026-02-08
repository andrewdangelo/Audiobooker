"""
MongoDB Service Layer
"""

__author__ = "Mohammad Saifan"

from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)


class MongoDBService:
    """Generic MongoDB service for collections"""

    def __init__(self, db, collection_name: str):
        """
        Initialize MongoDB service
        
        Args:
            db: MongoDB database instance
            collection_name: Name of the collection
        """
        self.db = db
        self.collection_name = collection_name
        self.collection = db[collection_name]

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new document"""
        try:
            # Add timestamps
            now = datetime.utcnow()
            data['created_at'] = now
            data['updated_at'] = now
            
            result = self.collection.insert_one(data)
            data['_id'] = result.inserted_id
            return data
        except Exception as e:
            logger.error(f"Error creating document in {self.collection_name}: {e}")
            raise e

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            return self.collection.find_one({"_id": ObjectId(item_id)})
        except Exception as e:
            logger.error(f"Error fetching document from {self.collection_name}: {e}")
            return None

    def get_all(self, skip: int = 0, limit: int = 20, filter_query: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all documents with pagination"""
        try:
            query = filter_query or {}
            cursor = self.collection.find(query).skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error fetching documents from {self.collection_name}: {e}")
            return []

    def count(self, filter_query: Optional[Dict] = None) -> int:
        """Count total documents"""
        try:
            query = filter_query or {}
            return self.collection.count_documents(query)
        except Exception as e:
            logger.error(f"Error counting documents in {self.collection_name}: {e}")
            return 0

    def update(self, item_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a document"""
        try:
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow()
            
            result = self.collection.find_one_and_update(
                {"_id": ObjectId(item_id)},
                {"$set": update_data},
                return_document=True  
            )
            return result
        except Exception as e:
            logger.error(f"Error updating document in {self.collection_name}: {e}")
            raise e

    def delete(self, item_id: str) -> bool:
        """Delete a document"""
        try:
            result = self.collection.delete_one({"_id": ObjectId(item_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting document from {self.collection_name}: {e}")
            return False

    def find_one(self, filter_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document matching the filter"""
        try:
            return self.collection.find_one(filter_query)
        except Exception as e:
            logger.error(f"Error finding document in {self.collection_name}: {e}")
            return None

    def find_many(self, filter_query: Dict[str, Any], skip: int = 0, limit: int = 20) -> List[Dict[str, Any]]:
        """Find multiple documents matching the filter"""
        try:
            cursor = self.collection.find(filter_query).skip(skip).limit(limit)
            return list(cursor)
        except Exception as e:
            logger.error(f"Error finding documents in {self.collection_name}: {e}")
            return []

    def update_many(self, filter_query: Dict[str, Any], update_data: Dict[str, Any]) -> int:
        """Update multiple documents"""
        try:
            update_data['updated_at'] = datetime.utcnow()
            result = self.collection.update_many(
                filter_query,
                {"$set": update_data}
            )
            return result.modified_count
        except Exception as e:
            logger.error(f"Error updating documents in {self.collection_name}: {e}")
            return 0

    def delete_many(self, filter_query: Dict[str, Any]) -> int:
        """Delete multiple documents"""
        try:
            result = self.collection.delete_many(filter_query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting documents from {self.collection_name}: {e}")
            return 0