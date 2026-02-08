"""
MongoDB Database Configuration and Connection Management

Uses Motor for async MongoDB operations.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import logging

from app.core.config_settings import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
            
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000
            )
            
            # Get database
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await cls.client.admin.command('ping')
            
            logger.info(f"Connected to MongoDB database: {settings.MONGODB_DB_NAME}")
            
            # Create indexes
            await cls._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB"""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from MongoDB")
    
    @classmethod
    async def _create_indexes(cls):
        """Create necessary indexes for collections"""
        try:
            # Users collection indexes
            users = cls.db.users
            await users.create_index("email", unique=True)
            await users.create_index("username", unique=True, sparse=True)
            await users.create_index("google_id", unique=True, sparse=True)
            
            # Refresh tokens collection indexes
            refresh_tokens = cls.db.refresh_tokens
            await refresh_tokens.create_index("token", unique=True)
            await refresh_tokens.create_index("user_id")
            await refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if cls.db is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return cls.db
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name"""
        return cls.get_db()[name]


# Convenience functions
def get_db() -> AsyncIOMotorDatabase:
    """Get database instance (for dependency injection)"""
    return MongoDB.get_db()


def get_users_collection():
    """Get users collection"""
    return MongoDB.get_collection("users")


def get_refresh_tokens_collection():
    """Get refresh tokens collection"""
    return MongoDB.get_collection("refresh_tokens")


def get_account_settings_collection():
    """Get account settings collection"""
    return MongoDB.get_collection("account_settings")
