"""
Contract tests: API proxy forwards to the correct service path and returns the
expected JSON shape when a request is queued (202).
"""
from unittest.mock import AsyncMock, patch

from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

from app.core.config_settings import settings
from main import app

PREFIX = settings.API_V1_PREFIX


async def _forward_stub(service_name: str, request: Request, path: str) -> Response:
    return Response(
        content=b'{"forwarded":true}',
        status_code=200,
        media_type="application/json",
    )


def test_backend_get_forwards_with_path_and_query():
    with (
        patch(
            "app.routers.proxy_router.QueueService.check_service_load",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.proxy_router.QueueService.acquire_service_slot",
            new_callable=AsyncMock,
            return_value="slot1",
        ),
        patch(
            "app.routers.proxy_router.QueueService.release_service_slot",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.proxy_router.RequestService.forward_request",
            new_callable=AsyncMock,
            side_effect=_forward_stub,
        ) as forward_mock,
    ):
        with TestClient(app) as client:
            r = client.get(
                f"{PREFIX}/backend/store/catalog",
                params={"page": "2", "limit": "5"},
            )
    assert r.status_code == 200
    assert r.json() == {"forwarded": True}
    assert forward_mock.await_count == 1
    call_kw = forward_mock.call_args
    assert call_kw[0][0] == "backend"
    assert call_kw[0][2] == "store/catalog"


def test_auth_post_json_queued_response_shape():
    with (
        patch(
            "app.routers.proxy_router.QueueService.check_service_load",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch(
            "app.routers.proxy_router.QueueService.get_queue_length",
            new_callable=AsyncMock,
            return_value=4,
        ),
        patch(
            "app.routers.proxy_router.QueueService.queue_request",
            new_callable=AsyncMock,
            return_value="queue_auth_abc123",
        ),
    ):
        with TestClient(app) as client:
            r = client.post(
                f"{PREFIX}/auth/login",
                json={"email": "a@b.com", "password": "x"},
            )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "queued"
    assert body["queue_id"] == "queue_auth_abc123"
    assert body["queue_position"] == 5
    assert body["check_status_url"] == "/queue/queue_auth_abc123"


def test_payment_post_forwards_when_capacity_available():
    with (
        patch(
            "app.routers.proxy_router.QueueService.check_service_load",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.routers.proxy_router.QueueService.acquire_service_slot",
            new_callable=AsyncMock,
            return_value="slot-p",
        ),
        patch(
            "app.routers.proxy_router.QueueService.release_service_slot",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.routers.proxy_router.RequestService.forward_request",
            new_callable=AsyncMock,
            side_effect=_forward_stub,
        ) as forward_mock,
    ):
        with TestClient(app) as client:
            r = client.post(
                f"{PREFIX}/payment/subscription/purchase",
                json={"user_id": "u1", "plan": "basic", "billing_cycle": "monthly"},
            )
    assert r.status_code == 200
    assert forward_mock.await_count == 1
    assert forward_mock.call_args[0][0] == "payment"
