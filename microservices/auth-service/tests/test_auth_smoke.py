"""
Smoke tests: signup and login contracts (happy path + invalid credentials).
"""

from starlette.testclient import TestClient

AUTH = "/api/v1/auth"


def test_signup_returns_tokens_and_user(client: TestClient):
    r = client.post(
        f"{AUTH}/signup",
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


def test_login_happy_path_after_signup(client: TestClient):
    client.post(
        f"{AUTH}/signup",
        json={
            "email": "smoke_login@example.com",
            "password": "SmokePass1",
            "first_name": "L",
            "last_name": "U",
        },
    )
    r = client.post(
        f"{AUTH}/login",
        json={"email": "smoke_login@example.com", "password": "SmokePass1"},
    )

    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "smoke_login@example.com"
    assert body["access_token"]


def test_login_invalid_password(client: TestClient):
    client.post(
        f"{AUTH}/signup",
        json={
            "email": "smoke_bad@example.com",
            "password": "SmokePass1",
            "first_name": "B",
            "last_name": "D",
        },
    )
    r = client.post(
        f"{AUTH}/login",
        json={"email": "smoke_bad@example.com", "password": "WrongPass1"},
    )

    assert r.status_code == 401


def test_signup_duplicate_email(client: TestClient):
    payload = {
        "email": "dup@example.com",
        "password": "SmokePass1",
        "first_name": "D",
        "last_name": "U",
    }
    r1 = client.post(f"{AUTH}/signup", json=payload)
    r2 = client.post(f"{AUTH}/signup", json=payload)

    assert r1.status_code == 201
    assert r2.status_code == 400
    assert "already" in r2.json()["detail"].lower()
