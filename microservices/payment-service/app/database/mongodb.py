"""
MongoDB Database Configuration and Connection Management

Uses Motor for async MongoDB operations.
Manages both Payment database and Auth database connections.
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from typing import Optional
import logging

from app.core.config_settings import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB connection manager for Payment Service"""
    
    # Payment database connection
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    
    # Auth database connection (read-only for user lookups)
    auth_client: Optional[AsyncIOMotorClient] = None
    auth_db: Optional[AsyncIOMotorDatabase] = None
    
    @classmethod
    async def connect(cls):
        """Connect to MongoDB databases"""
        try:
            # Connect to Payment database
            logger.info(f"Connecting to Payment MongoDB at {settings.MONGODB_URL}...")
            
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000
            )
            
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            await cls.client.admin.command('ping')
            logger.info(f"Connected to Payment MongoDB database: {settings.MONGODB_DB_NAME}")
            
            # Connect to Auth database (for user lookups)
            logger.info(f"Connecting to Auth MongoDB at {settings.AUTH_MONGODB_URL}...")
            
            cls.auth_client = AsyncIOMotorClient(
                settings.AUTH_MONGODB_URL,
                maxPoolSize=5,  # Smaller pool for read-only access
                minPoolSize=1,
                serverSelectionTimeoutMS=5000
            )
            
            cls.auth_db = cls.auth_client[settings.AUTH_MONGODB_DB_NAME]
            await cls.auth_client.admin.command('ping')
            logger.info(f"Connected to Auth MongoDB database: {settings.AUTH_MONGODB_DB_NAME}")
            
            # Create indexes
            await cls._create_indexes()
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise
    
    @classmethod
    async def disconnect(cls):
        """Disconnect from MongoDB databases"""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from Payment MongoDB")
        if cls.auth_client:
            cls.auth_client.close()
            logger.info("Disconnected from Auth MongoDB")
    
    @classmethod
    async def _create_indexes(cls):
        """Create necessary indexes for collections"""
        try:
            # Payments collection indexes
            payments = cls.db.payments
            await payments.create_index("user_id")
            await payments.create_index("stripe_payment_intent_id", unique=True, sparse=True)
            await payments.create_index("stripe_checkout_session_id", unique=True, sparse=True)
            await payments.create_index("status")
            await payments.create_index("created_at")
            
            # Orders collection indexes
            orders = cls.db.orders
            await orders.create_index("user_id")
            await orders.create_index("payment_id")
            await orders.create_index("status")
            await orders.create_index("created_at")
            
            # Webhook events collection (for idempotency)
            webhook_events = cls.db.webhook_events
            await webhook_events.create_index("stripe_event_id", unique=True)
            await webhook_events.create_index("created_at")
            
            # Subscriptions collection (if needed later)
            subscriptions = cls.db.subscriptions
            await subscriptions.create_index("user_id")
            await subscriptions.create_index("stripe_subscription_id", unique=True, sparse=True)
            await subscriptions.create_index("status")
            
            logger.info("MongoDB indexes created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")
    
    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the payment database instance"""
        if cls.db is None:
            raise RuntimeError("Payment database not connected")
        return cls.db
    
    @classmethod
    def get_auth_db(cls) -> AsyncIOMotorDatabase:
        """Get the auth database instance (read-only access)"""
        if cls.auth_db is None:
            raise RuntimeError("Auth database not connected")
        return cls.auth_db
    
    @classmethod
    async def get_user_by_id(cls, user_id: str) -> Optional[dict]:
        """Get user from auth database by ID"""
        try:
            from bson import ObjectId
            users = cls.auth_db.users
            user = await users.find_one({"_id": ObjectId(user_id)})
            return user
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            return None
    
    @classmethod
    async def get_user_by_email(cls, email: str) -> Optional[dict]:
        """Get user from auth database by email"""
        try:
            users = cls.auth_db.users
            user = await users.find_one({"email": email})
            return user
        except Exception as e:
            logger.error(f"Error fetching user by email: {str(e)}")
            return None
