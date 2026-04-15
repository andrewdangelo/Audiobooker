"""Test doubles: async Mongo collections backed by mongomock."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import mongomock
import pytest

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


@pytest.fixture
def auth_mongo_wired():
    MongoDB.client = MagicMock()
    MongoDB.db = _FakeAsyncDb()
    yield MongoDB.db
    MongoDB.client = None
    MongoDB.db = None
