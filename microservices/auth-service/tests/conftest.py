"""Test doubles: async Mongo collections backed by mongomock."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import mongomock
import pytest
from starlette.testclient import TestClient

from app.database.mongodb import MongoDB


class _AsyncCollection:
    def __init__(self, coll: mongomock.Collection):
        self._c = coll

    async def find_one(self, *args, **kwargs):
        return await asyncio.to_thread(self._c.find_one, *args, **kwargs)

    async def insert_one(self, document):
        return await asyncio.to_thread(self._c.insert_one, document)

    async def update_one(self, *args, **kwargs):
        return await asyncio.to_thread(self._c.update_one, *args, **kwargs)

    async def create_index(self, *args, **kwargs):
        return await asyncio.to_thread(self._c.create_index, *args, **kwargs)


class _FakeAsyncDb:
    """Minimal stand-in for AsyncIOMotorDatabase (subscriptable collections only)."""

    def __init__(self, name: str = "auth_contract_test"):
        self._db = mongomock.MongoClient()[name]

    def __getitem__(self, name: str) -> _AsyncCollection:
        return _AsyncCollection(self._db[name])


async def _fake_mongo_connect(cls):
    cls.client = MagicMock()
    cls.db = _FakeAsyncDb()


async def _fake_mongo_disconnect(cls):
    return None


@pytest.fixture
def client():
    """Auth TestClient with MongoDB wired to mongomock (no real Motor connect)."""

    from main import app

    with (
        patch.object(MongoDB, "connect", classmethod(_fake_mongo_connect)),
        patch.object(MongoDB, "disconnect", classmethod(_fake_mongo_disconnect)),
    ):
        with TestClient(app) as c:
            yield c

    MongoDB.client = None
    MongoDB.db = None
