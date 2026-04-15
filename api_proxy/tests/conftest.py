"""Avoid real Redis / queue workers during API proxy tests."""

import os

# Must run before importing the app (slowapi storage is chosen at import time).
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _noop_proxy_lifecycle():
    with (
        patch("main.redis_manager._ensure_connection", new_callable=AsyncMock),
        patch("main.start_queue_workers", new_callable=AsyncMock),
        patch("main.stop_queue_workers", new_callable=AsyncMock),
        patch("main.redis_manager.disconnect", new_callable=AsyncMock),
    ):
        yield
