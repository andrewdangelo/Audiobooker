"""
Contract tests for store catalog, purchase fulfillment, and internal library API.
Uses mongomock (no real MongoDB required).
"""
import mongomock
import pytest
from starlette.testclient import TestClient

import app.database.database as db_module
from app.models.db_models import Collections
from app.core import config_settings


@pytest.fixture(autouse=True)
def reset_mongo():
    db_module.sync_client = mongomock.MongoClient()
    yield
    db_module.sync_client = None


@pytest.fixture(autouse=True)
def internal_key(monkeypatch):
    monkeypatch.setattr(config_settings.settings, "INTERNAL_SERVICE_KEY", "test-internal-key")


@pytest.fixture
def books_db():
    db = db_module.get_database()
    coll = db[Collections.BOOKS]
    coll.insert_one(
        {
            "_id": "book-store-1",
            "id": "book-store-1",
            "title": "Contract Book",
            "author": "Tester",
            "is_store_item": True,
            "genre": "fiction",
            "rating": 4.2,
            "review_count": 10,
            "price": 9.99,
            "credits_required": 1,
            "is_premium": False,
        }
    )
    return db


def test_get_store_catalog_shape(books_db):
    from main import app

    with TestClient(app) as client:
        r = client.get("/api/v1/store/catalog")

    assert r.status_code == 200
    data = r.json()
    assert "books" in data and "total" in data and "page" in data
    assert data["total"] == 1
    assert len(data["books"]) == 1
    assert data["books"][0]["id"] == "book-store-1"
    assert data["books"][0]["title"] == "Contract Book"


def test_post_store_purchase_adds_library(books_db):
    from main import app

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/store/purchase",
            params={"user_id": "user-1"},
            json={"book_id": "book-store-1", "purchase_type": "basic"},
        )

    assert r.status_code == 200
    assert r.json()["success"] is True
    db = db_module.get_database()
    lib = db[Collections.USER_LIBRARY].find_one(
        {"user_id": "user-1", "book_id": "book-store-1"}
    )
    assert lib is not None
    assert lib.get("purchase_type") == "basic"


def test_post_store_purchase_idempotent(books_db):
    from main import app

    db = db_module.get_database()
    db[Collections.USER_LIBRARY].insert_one(
        {
            "user_id": "user-2",
            "book_id": "book-store-1",
            "progress": 0.0,
            "purchase_type": "basic",
        }
    )

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/store/purchase",
            params={"user_id": "user-2"},
            json={"book_id": "book-store-1"},
        )

    assert r.status_code == 200
    assert r.json()["message"] == "Already owned"


def test_internal_library_requires_key(books_db):
    from main import app

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/internal/library/user-svc",
            json={"book_id": "book-store-1"},
        )
    assert r.status_code == 403


def test_internal_library_create_and_idempotent(books_db):
    from main import app

    with TestClient(app) as client:
        r1 = client.post(
            "/api/v1/internal/library/user-svc",
            json={"book_id": "book-store-1"},
            headers={"X-Internal-Service-Key": "test-internal-key"},
        )
        r2 = client.post(
            "/api/v1/internal/library/user-svc",
            json={"book_id": "book-store-1"},
            headers={"X-Internal-Service-Key": "test-internal-key"},
        )

    assert r1.status_code == 201
    assert r1.json()["created"] is True
    assert r2.status_code == 201
    assert r2.json()["created"] is False
    assert r2.json()["entry"]["book_id"] == "book-store-1"
