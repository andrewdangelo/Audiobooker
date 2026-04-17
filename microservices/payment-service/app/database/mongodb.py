"""
MongoDB Database Configuration and Connection Management

Uses Motor for async MongoDB operations.
Manages the Payment database only.  Access to other services' data is handled
via HTTP calls through the API proxy (see app/services/service_client.py).
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

    @classmethod
    async def connect(cls):
        """Connect to the Payment MongoDB database."""
        try:
            logger.info(f"Connecting to Payment MongoDB at {settings.MONGODB_URL}...")

            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                serverSelectionTimeoutMS=5000,
            )

            cls.db = cls.client[settings.MONGODB_DB_NAME]
            await cls.client.admin.command("ping")
            logger.info(f"Connected to Payment MongoDB database: {settings.MONGODB_DB_NAME}")

            await cls._create_indexes()

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    @classmethod
    async def disconnect(cls):
        """Disconnect from the Payment MongoDB database."""
        if cls.client:
            cls.client.close()
            logger.info("Disconnected from Payment MongoDB")

    @classmethod
    async def _create_indexes(cls):
        """Create necessary indexes for collections."""
        try:
            payments = cls.db.payments
            await payments.create_index("user_id")
            await payments.create_index("stripe_payment_intent_id", unique=True, sparse=True)
            await payments.create_index("stripe_checkout_session_id", unique=True, sparse=True)
            await payments.create_index("status")
            await payments.create_index("created_at")

            orders = cls.db.orders
            await orders.create_index("user_id")
            await orders.create_index("payment_id")
            await orders.create_index("status")
            await orders.create_index("created_at")

            webhook_events = cls.db.webhook_events
            await webhook_events.create_index("stripe_event_id", unique=True)
            await webhook_events.create_index("created_at")

            subscriptions = cls.db.subscriptions
            await subscriptions.create_index("user_id")
            await subscriptions.create_index("stripe_subscription_id", unique=True, sparse=True)
            await subscriptions.create_index("status")

            logger.info("MongoDB indexes created successfully")

        except Exception as e:
            logger.error(f"Failed to create indexes: {str(e)}")

    @classmethod
    def get_db(cls) -> AsyncIOMotorDatabase:
        """Get the payment database instance."""
        if cls.db is None:
            raise RuntimeError("Payment database not connected")
        return cls.db

