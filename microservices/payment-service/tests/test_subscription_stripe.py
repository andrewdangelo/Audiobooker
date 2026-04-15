"""
Subscription purchase guards and Stripe checkout creation (mocked).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from app.database.mongodb import MongoDB
from app.models.schemas import BillingCycle, SubscriptionPlan
from app.core.config_settings import settings
from main import app


def _subscription_db_mock():
    oid = ObjectId()
    subs = MagicMock()
    subs.insert_one = AsyncMock(return_value=MagicMock(inserted_id=oid))
    subs.update_one = AsyncMock()
    db = MagicMock()
    db.subscriptions = subs
    return db, oid


@pytest.mark.asyncio
async def test_purchase_already_subscribed_same_plan(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_BASIC_MONTHLY_PRICE_ID", "price_test_basic")

    async def _user(_uid):
        return {
            "_id": _uid,
            "subscription_plan": "basic",
            "subscription_status": "active",
            "subscription_billing_cycle": "monthly",
            "subscription_end_date": None,
        }

    mock_db, _ = _subscription_db_mock()
    transport = ASGITransport(app=app, lifespan="off")
    with (
        patch(
            "app.routers.subscription.service_client.get_user_by_id",
            new_callable=AsyncMock,
            side_effect=_user,
        ),
        patch.object(MongoDB, "get_db", return_value=mock_db),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/subscription/purchase",
                json={
                    "user_id": "507f1f77bcf86cd799439011",
                    "plan": "basic",
                    "billing_cycle": "monthly",
                },
            )

    assert r.status_code == 200
    body = r.json()
    assert body["already_subscribed"] is True
    assert body["status"] == "already_subscribed"
    mock_db.subscriptions.insert_one.assert_not_called()


@pytest.mark.asyncio
async def test_purchase_creates_checkout_session_with_mocked_stripe(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_BASIC_MONTHLY_PRICE_ID", "price_test_basic")

    async def _user(_uid):
        return {
            "_id": _uid,
            "subscription_plan": "none",
            "subscription_status": "none",
            "subscription_discount_applied": False,
            "subscription_cancelled_at": None,
        }

    mock_db, oid = _subscription_db_mock()
    fake_session = MagicMock()
    fake_session.id = "cs_test_contract"
    fake_session.url = "https://checkout.stripe.test/c/session"

    transport = ASGITransport(app=app, lifespan="off")
    with (
        patch(
            "app.routers.subscription.service_client.get_user_by_id",
            new_callable=AsyncMock,
            side_effect=_user,
        ),
        patch.object(MongoDB, "get_db", return_value=mock_db),
        patch(
            "app.routers.subscription.stripe.checkout.Session.create",
            return_value=fake_session,
        ) as create_session,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/subscription/purchase",
                json={
                    "user_id": "507f1f77bcf86cd799439011",
                    "plan": "basic",
                    "billing_cycle": "monthly",
                },
            )

    assert r.status_code == 200
    body = r.json()
    assert body["already_subscribed"] is False
    assert body["checkout_url"] == "https://checkout.stripe.test/c/session"
    assert body["status"] == "pending"
    create_session.assert_called_once()
    call_kw = create_session.call_args.kwargs
    assert call_kw["mode"] == "subscription"
    assert call_kw["line_items"] == [{"price": "price_test_basic", "quantity": 1}]
    mock_db.subscriptions.insert_one.assert_awaited()
    mock_db.subscriptions.update_one.assert_awaited()


@pytest.mark.asyncio
async def test_purchase_retention_discount_uses_mocked_coupon_and_stripe(monkeypatch):
    monkeypatch.setattr(settings, "STRIPE_PREMIUM_MONTHLY_PRICE_ID", "price_test_premium")

    async def _user(_uid):
        return {
            "_id": _uid,
            "subscription_plan": "none",
            "subscription_status": "none",
            "subscription_discount_applied": False,
            "subscription_cancelled_at": "2025-01-01T00:00:00",
        }

    mock_db, _ = _subscription_db_mock()
    fake_session = MagicMock()
    fake_session.id = "cs_test_retention"
    fake_session.url = "https://checkout.stripe.test/c/retention"

    fake_coupon = MagicMock()
    fake_coupon.id = "coupon_test_ret"

    transport = ASGITransport(app=app, lifespan="off")
    with (
        patch(
            "app.routers.subscription.service_client.get_user_by_id",
            new_callable=AsyncMock,
            side_effect=_user,
        ),
        patch.object(MongoDB, "get_db", return_value=mock_db),
        patch(
            "app.routers.subscription.stripe.Coupon.create",
            return_value=fake_coupon,
        ) as coupon_create,
        patch(
            "app.routers.subscription.stripe.checkout.Session.create",
            return_value=fake_session,
        ) as create_session,
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/subscription/purchase",
                json={
                    "user_id": "507f1f77bcf86cd799439011",
                    "plan": "premium",
                    "billing_cycle": "monthly",
                    "apply_discount": True,
                },
            )

    assert r.status_code == 200
    coupon_create.assert_called_once()
    create_session.assert_called_once()
    assert "discounts" in create_session.call_args.kwargs
