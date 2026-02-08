"""
MongoDB Database Configuration
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from typing import Optional
import logging

from app.core.config_settings import settings

logger = logging.getLogger(__name__)

# Async MongoDB client for async operations
async_client: Optional[AsyncIOMotorClient] = None
# Sync MongoDB client for sync operations
sync_client: Optional[MongoClient] = None


def get_database(db_name=settings.DATABASE_NAME):
    """
    Get MongoDB database instance (sync)
    
    Usage:
        db = get_database()
        collection = db["users"]
    """
    global sync_client
    if sync_client is None:
        sync_client = MongoClient(settings.DATABASE_URL)
    return sync_client[db_name]

async def get_async_database(db_name=settings.DATABASE_NAME):
    """
    Get async MongoDB database instance
    
    Usage:
        db = await get_async_database()
        collection = db["users"]
    """
    global async_client
    if async_client is None:
        async_client = AsyncIOMotorClient(settings.DATABASE_URL)
    return async_client[db_name]


def get_db(db_name=settings.DATABASE_NAME):
    """
    Dependency function to get database instance
    """
    def _get_db():
        return next(establish_mongodb_connection(db_name))
    
    return _get_db
    
def establish_mongodb_connection(db_name=settings.DATABASE_NAME):
    """
    Dependency function to get database instance
    
    Usage:
        @app.get("/items")
        def get_items(db = Depends(get_db)):
            ...
    """
    try:
        db = get_database(db_name=db_name)
        yield db
    finally:
        pass  

async def connect_to_mongodb():
    """Initialize MongoDB connection"""
    global async_client, sync_client
    try:
        # Initialize async client
        async_client = AsyncIOMotorClient(settings.DATABASE_URL)
        # Test connection
        await async_client.admin.command('ping')
        
        # Initialize sync client
        sync_client = MongoClient(settings.DATABASE_URL)
        sync_client.admin.command('ping')
        
        logger.info(f"Connected to MongoDB at {settings.DATABASE_URL}")
        logger.info(f"Using database: {settings.DATABASE_NAME}")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongodb_connection():
    """Close MongoDB connection"""
    global async_client, sync_client
    if async_client:
        async_client.close()
        logger.info("Closed async MongoDB connection")
    if sync_client:
        sync_client.close()
        logger.info("Closed sync MongoDB connection")