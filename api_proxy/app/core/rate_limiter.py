"""
Rate limiter configuration
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from app.core.config_settings import settings

_storage_uri = settings.RATE_LIMIT_STORAGE_URI or (
    f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}"
)

# Rate limits: Redis in normal runs; optional memory:// for tests (RATE_LIMIT_STORAGE_URI)
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    default_limits=[f"{settings.RATE_LIMIT_PER_HOUR}/hour"],
)



