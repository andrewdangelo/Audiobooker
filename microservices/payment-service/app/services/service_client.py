"""
Service Client

HTTP client for inter-service communication. Instead of accessing other
services' databases directly, the payment service uses this client to call
the API proxy, which forwards requests to the appropriate microservice.

Proxy base: settings.PROXY_URL  (e.g. http://localhost:8000/api/v1/audiobooker_proxy)
  Auth  calls → /auth/internal/...   (forwarded to auth-service)
  Backend calls → /backend/internal/... (forwarded to backend-service)

All requests include the X-Internal-Service-Key header so the receiving
service can reject calls that don't come from a trusted source.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

import httpx

from app.core.config_settings import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0  # seconds


def _internal_headers() -> dict:
    return {"X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY}


def _auth_url(path: str) -> str:
    """Build a proxy URL that targets the auth service's internal endpoint."""
    return f"{settings.PROXY_URL}/auth/internal/{path.lstrip('/')}"


def _backend_url(path: str) -> str:
    """Build a proxy URL that targets the backend service's internal endpoint."""
    return f"{settings.PROXY_URL}/backend/internal/{path.lstrip('/')}"


# ---------------------------------------------------------------------------
# Auth-service: user reads
# ---------------------------------------------------------------------------

async def get_user_by_id(user_id: str) -> Optional[dict]:
    """Fetch a user document from the auth-service by MongoDB ObjectId."""
    url = _auth_url(f"users/{user_id}")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_internal_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] get_user_by_id HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"[service_client] get_user_by_id error: {e}")
        return None


async def get_user_by_stripe_subscription(stripe_sub_id: str) -> Optional[dict]:
    """Fetch a user document from the auth-service by their Stripe subscription ID."""
    url = _auth_url(f"users/by-stripe-subscription/{stripe_sub_id}")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_internal_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] get_user_by_stripe_subscription HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"[service_client] get_user_by_stripe_subscription error: {e}")
        return None


# ---------------------------------------------------------------------------
# Auth-service: user writes
# ---------------------------------------------------------------------------

async def update_user_subscription(user_id: str, fields: Dict[str, Any]) -> bool:
    """
    Overwrite subscription-related fields on the user via the auth-service.

    ``fields`` should contain only the keys you want to $set, e.g.:
        {"subscription_plan": "basic", "subscription_status": "active", ...}
    Datetime values should be datetime objects or ISO-format strings.
    """
    url = _auth_url(f"users/{user_id}/subscription")

    # Convert datetime objects to ISO strings for JSON serialisation
    payload: Dict[str, Any] = {}
    for k, v in fields.items():
        payload[k] = v.isoformat() if isinstance(v, datetime) else v

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.patch(url, json=payload, headers=_internal_headers())
        resp.raise_for_status()
        return resp.json().get("updated", False)
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] update_user_subscription HTTP error: {e} body={e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[service_client] update_user_subscription error: {e}")
        return False


async def update_user_credits(user_id: str, increments: Dict[str, int]) -> bool:
    """
    Atomically increment (or decrement) credit fields on the user via the auth-service.

    ``increments`` maps field name → integer delta, e.g.:
        {"basic_credits": 5, "credits": 5}        # add 5 basic credits
        {"premium_credits": -2, "credits": -2}    # deduct 2 premium credits
    """
    url = _auth_url(f"users/{user_id}/credits")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.patch(url, json=increments, headers=_internal_headers())
        resp.raise_for_status()
        return resp.json().get("updated", False)
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] update_user_credits HTTP error: {e} body={e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[service_client] update_user_credits error: {e}")
        return False


# ---------------------------------------------------------------------------
# Backend-service: library
# ---------------------------------------------------------------------------

async def get_library_entry(user_id: str, book_id: str) -> Optional[dict]:
    """Check whether a book is already in a user's library."""
    url = _backend_url(f"library/{user_id}/{book_id}")
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url, headers=_internal_headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] get_library_entry HTTP error: {e}")
        return None
    except Exception as e:
        logger.error(f"[service_client] get_library_entry error: {e}")
        return None


async def add_library_entry(
    user_id: str,
    book_id: str,
    progress: float = 0.0,
    order_id: Optional[str] = None,
    added_at: Optional[datetime] = None,
) -> bool:
    """Add a book to the user's library via the backend-service. Returns True if created."""
    url = _backend_url(f"library/{user_id}")
    payload = {
        "book_id": book_id,
        "progress": progress,
        "last_played_at": None,
        "added_at": (added_at or datetime.utcnow()).isoformat(),
        "completed": False,
        "order_id": order_id,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_internal_headers())
        resp.raise_for_status()
        return resp.json().get("created", False)
    except httpx.HTTPStatusError as e:
        logger.error(f"[service_client] add_library_entry HTTP error: {e} body={e.response.text}")
        return False
    except Exception as e:
        logger.error(f"[service_client] add_library_entry error: {e}")
        return False
