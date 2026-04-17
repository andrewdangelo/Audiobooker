"""
Test Client Factory
===================
Builds the three dependencies VoiceLibraryManager needs:

    collection  — Motor async Mongo collection (voice_library)
    r2_session  — aioboto3 Session (lazy; no connection opened yet)
    r2_config   — dict of R2 credentials/bucket pulled from settings

Import pattern in every test:
    from tests.client_factory import get_clients
    collection, r2_session, r2_config = get_clients()
"""

import aioboto3
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config_settings import settings


def get_clients():
    """
    Returns (collection, r2_session, r2_config).

    Deliberately synchronous — Motor and aioboto3 do their real async work
    only when you await calls, so building the objects here is safe and keeps
    test setup simple (no async fixtures needed).
    """
    # --- Mongo ---
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = mongo_client["audiobooker_backend_db"]          # adjust db name if yours differs
    collection = db["voice_library"]

    # --- R2 (Cloudflare) ---
    r2_session = aioboto3.Session()
    r2_config = {
        "account_id": settings.R2_ACCOUNT_ID,
        "access_key": settings.R2_ACCESS_KEY_ID,
        "secret_key": settings.R2_SECRET_ACCESS_KEY,
        "bucket":     settings.R2_BUCKET_NAME,
    }

    return collection, r2_session, r2_config