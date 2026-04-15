"""
Smoke tests: signup and login contracts (happy path + invalid credentials).
Runs without a real MongoDB by wiring MongoDB.db to mongomock-backed async collections.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.asyncio
async def test_signup_returns_tokens_and_user(auth_mongo_wired):
    transport = ASGITransport(app=app, lifespan="off")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/signup",
            json={
                "email": "smoke_signup@example.com",
                "password": "SmokePass1",
                "first_name": "Smoke",
                "last_name": "User",
            },
        )

    assert r.status_code == 201
    body = r.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body and "refresh_token" in body
    assert body["user"]["email"] == "smoke_signup@example.com"


@pytest.mark.asyncio
async def test_login_happy_path_after_signup(auth_mongo_wired):
    transport = ASGITransport(app=app, lifespan="off")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/signup",
            json={
                "email": "smoke_login@example.com",
                "password": "SmokePass1",
                "first_name": "L",
                "last_name": "U",
            },
        )
        r = await client.post(
            "/api/v1/login",
            json={"email": "smoke_login@example.com", "password": "SmokePass1"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "smoke_login@example.com"
    assert body["access_token"]


@pytest.mark.asyncio
async def test_login_invalid_password(auth_mongo_wired):
    transport = ASGITransport(app=app, lifespan="off")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/signup",
            json={
                "email": "smoke_bad@example.com",
                "password": "SmokePass1",
                "first_name": "B",
                "last_name": "D",
            },
        )
        r = await client.post(
            "/api/v1/login",
            json={"email": "smoke_bad@example.com", "password": "WrongPass1"},
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_signup_duplicate_email(auth_mongo_wired):
    transport = ASGITransport(app=app, lifespan="off")
    payload = {
        "email": "dup@example.com",
        "password": "SmokePass1",
        "first_name": "D",
        "last_name": "U",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/api/v1/signup", json=payload)
        r2 = await client.post("/api/v1/signup", json=payload)

    assert r1.status_code == 201
    assert r2.status_code == 400
    assert "already" in r2.json()["detail"].lower()
