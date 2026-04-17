"""
Canonical pricing catalog for subscriptions and one-time credit packs.
"""

from __future__ import annotations

from typing import Any, Dict

from app.models.schemas import BillingCycle, SubscriptionPlan


SUBSCRIPTION_CATALOG: Dict[SubscriptionPlan, Dict[str, Any]] = {
    SubscriptionPlan.BASIC: {
        "id": SubscriptionPlan.BASIC.value,
        "name": "Basic",
        "description": "Single-voice narration for standard listening.",
        "included_credit_type": "basic",
        "included_credits": 1,
        "features": [
            "1 Basic credit per billing cycle",
            "Single voice narration",
            "Standard processing speed",
            "MP3 downloads",
        ],
        "prices": {
            BillingCycle.MONTHLY: 999,
            BillingCycle.ANNUAL: 9999,
        },
    },
    SubscriptionPlan.PREMIUM: {
        "id": SubscriptionPlan.PREMIUM.value,
        "name": "Premium",
        "description": "Theatrical narration with multiple character voices.",
        "included_credit_type": "premium",
        "included_credits": 1,
        "features": [
            "1 Premium credit per billing cycle",
            "Multiple character voices",
            "Priority processing",
            "Expanded voice library",
        ],
        "prices": {
            BillingCycle.MONTHLY: 1999,
            BillingCycle.ANNUAL: 19999,
        },
    },
    SubscriptionPlan.PUBLISHER: {
        "id": SubscriptionPlan.PUBLISHER.value,
        "name": "Publisher",
        "description": "Premium narration plus publishing and distribution tools.",
        "included_credit_type": "premium",
        "included_credits": 1,
        "features": [
            "1 Premium credit per billing cycle",
            "All Premium features",
            "Publishing toolkit",
            "Commercial distribution support",
        ],
        "prices": {
            BillingCycle.MONTHLY: 2999,
            BillingCycle.ANNUAL: 29999,
        },
    },
}


CREDIT_PACK_CATALOG: Dict[str, Dict[str, Any]] = {
    "basic-1": {
        "id": "basic-1",
        "name": "1 Basic Credit",
        "description": "Single voice narration",
        "credit_type": "basic",
        "credits": 1,
        "amount_cents": 1495,
    },
    "basic-3": {
        "id": "basic-3",
        "name": "3 Basic Credits",
        "description": "Single voice narration",
        "credit_type": "basic",
        "credits": 3,
        "amount_cents": 4299,
    },
    "basic-5": {
        "id": "basic-5",
        "name": "5 Basic Credits",
        "description": "Single voice narration",
        "credit_type": "basic",
        "credits": 5,
        "amount_cents": 6999,
    },
    "basic-10": {
        "id": "basic-10",
        "name": "10 Basic Credits",
        "description": "Single voice narration",
        "credit_type": "basic",
        "credits": 10,
        "amount_cents": 12999,
    },
    "premium-1": {
        "id": "premium-1",
        "name": "1 Premium Credit",
        "description": "Multiple character voices",
        "credit_type": "premium",
        "credits": 1,
        "amount_cents": 2495,
    },
    "premium-3": {
        "id": "premium-3",
        "name": "3 Premium Credits",
        "description": "Multiple character voices",
        "credit_type": "premium",
        "credits": 3,
        "amount_cents": 7199,
    },
    "premium-5": {
        "id": "premium-5",
        "name": "5 Premium Credits",
        "description": "Multiple character voices",
        "credit_type": "premium",
        "credits": 5,
        "amount_cents": 11799,
    },
    "premium-10": {
        "id": "premium-10",
        "name": "10 Premium Credits",
        "description": "Multiple character voices",
        "credit_type": "premium",
        "credits": 10,
        "amount_cents": 22999,
    },
}


def get_subscription_price(plan: SubscriptionPlan, billing_cycle: BillingCycle) -> int:
    return SUBSCRIPTION_CATALOG[plan]["prices"][billing_cycle]


def get_subscription_credit_grant(plan: SubscriptionPlan | str) -> Dict[str, int]:
    normalized_plan = SubscriptionPlan(plan)
    catalog_item = SUBSCRIPTION_CATALOG[normalized_plan]
    credit_type = catalog_item["included_credit_type"]
    credits = catalog_item["included_credits"]
    typed_field = "premium_credits" if credit_type == "premium" else "basic_credits"
    return {
        typed_field: credits,
        "credits": credits,
    }


def serialize_subscription_catalog() -> list[dict[str, Any]]:
    plans: list[dict[str, Any]] = []
    for plan, item in SUBSCRIPTION_CATALOG.items():
        plans.append(
            {
                "id": item["id"],
                "name": item["name"],
                "description": item["description"],
                "included_credit_type": item["included_credit_type"],
                "included_credits": item["included_credits"],
                "monthly_amount_cents": item["prices"][BillingCycle.MONTHLY],
                "annual_amount_cents": item["prices"][BillingCycle.ANNUAL],
                "features": item["features"],
            }
        )
    return plans


def serialize_credit_pack_catalog(credit_type: str | None = None) -> list[dict[str, Any]]:
    packs = list(CREDIT_PACK_CATALOG.values())
    if credit_type:
        packs = [pack for pack in packs if pack["credit_type"] == credit_type]
    return packs
