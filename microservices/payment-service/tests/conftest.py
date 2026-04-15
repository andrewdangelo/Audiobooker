from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from app.database.mongodb import MongoDB


async def _fake_pay_connect(cls):
    cls.client = MagicMock()
    cls.db = MagicMock()


async def _fake_pay_disconnect(cls):
    return None


@pytest.fixture
def client():
    """Payment TestClient: no real Mongo on lifespan (tests patch get_db per case)."""

    from main import app

    with (
        patch.object(MongoDB, "connect", classmethod(_fake_pay_connect)),
        patch.object(MongoDB, "disconnect", classmethod(_fake_pay_disconnect)),
    ):
        with TestClient(app) as c:
            yield c

    MongoDB.client = None
    MongoDB.db = None
