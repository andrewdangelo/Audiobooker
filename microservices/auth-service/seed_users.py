"""
Seed Script: User Profiles → MongoDB (auth-service)

Usage:
    python seed_users.py              # insert seed users (skip existing)
    python seed_users.py --wipe       # drop users collection first, then seed
    python seed_users.py --check      # print current users in DB and exit
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import hashlib
import base64
from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MONGODB_URL    = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
MONGODB_DB     = os.getenv("MONGODB_DB_NAME", "audiobooker_auth")
COLLECTION     = "users"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def hash_pw(plain: str) -> str:
    """Match auth service: SHA-256 pre-hash → bcrypt (see app/utils/security.py)"""
    sha256_hash = hashlib.sha256(plain.encode("utf-8")).digest()
    prehashed = base64.b64encode(sha256_hash)
    return bcrypt.hashpw(prehashed, bcrypt.gensalt()).decode("utf-8")


# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
NOW = datetime.utcnow()

SEED_USERS = [
    # ── Admin / superuser ───────────────────────────────────────────────────
    {
        "email": "admin@audiobooker.com",
        "username": "admin",
        "first_name": "Admin",
        "last_name": "User",
        "hashed_password": hash_pw("Admin@1234!"),
        "is_active": True,
        "is_verified": True,
        "auth_provider": "local",
        "credits": 999,
        "basic_credits": 999,
        "premium_credits": 999,
        "subscription_plan": "premium",
        "subscription_status": "active",
        "subscription_billing_cycle": "annual",
        "subscription_start_date": NOW - timedelta(days=30),
        "subscription_end_date": NOW + timedelta(days=335),
        "subscription_discount_applied": False,
        "created_at": NOW,
        "updated_at": NOW,
    },

    # ── Free-tier user (default credits only) ───────────────────────────────
    {
        "email": "alice@example.com",
        "username": "alice",
        "first_name": "Alice",
        "last_name": "Johnson",
        "hashed_password": hash_pw("Password123!"),
        "is_active": True,
        "is_verified": True,
        "auth_provider": "local",
        "credits": 3,
        "basic_credits": 3,
        "premium_credits": 0,
        "subscription_plan": "none",
        "subscription_status": "none",
        "created_at": NOW - timedelta(days=10),
        "updated_at": NOW - timedelta(days=10),
    },

    # ── Basic subscriber ─────────────────────────────────────────────────────
    {
        "email": "bob@example.com",
        "username": "bob_reads",
        "first_name": "Bob",
        "last_name": "Smith",
        "hashed_password": hash_pw("Password123!"),
        "is_active": True,
        "is_verified": True,
        "auth_provider": "local",
        "credits": 10,
        "basic_credits": 10,
        "premium_credits": 0,
        "subscription_plan": "basic",
        "subscription_status": "active",
        "subscription_billing_cycle": "monthly",
        "subscription_start_date": NOW - timedelta(days=15),
        "subscription_end_date": NOW + timedelta(days=15),
        "subscription_discount_applied": False,
        "created_at": NOW - timedelta(days=15),
        "updated_at": NOW - timedelta(days=15),
    },

    # ── Premium subscriber (monthly) ─────────────────────────────────────────
    {
        "email": "carol@example.com",
        "username": "carol_premium",
        "first_name": "Carol",
        "last_name": "Williams",
        "hashed_password": hash_pw("Password123!"),
        "is_active": True,
        "is_verified": True,
        "auth_provider": "local",
        "credits": 50,
        "basic_credits": 25,
        "premium_credits": 25,
        "subscription_plan": "premium",
        "subscription_status": "active",
        "subscription_billing_cycle": "monthly",
        "subscription_start_date": NOW - timedelta(days=5),
        "subscription_end_date": NOW + timedelta(days=25),
        "subscription_discount_applied": False,
        "created_at": NOW - timedelta(days=5),
        "updated_at": NOW - timedelta(days=5),
    },

    # ── Cancelled subscriber (still in grace period) ─────────────────────────
    {
        "email": "dave@example.com",
        "username": "dave_cancelled",
        "first_name": "Dave",
        "last_name": "Brown",
        "hashed_password": hash_pw("Password123!"),
        "is_active": True,
        "is_verified": True,
        "auth_provider": "local",
        "credits": 2,
        "basic_credits": 2,
        "premium_credits": 0,
        "subscription_plan": "basic",
        "subscription_status": "pending_cancellation",
        "subscription_billing_cycle": "monthly",
        "subscription_start_date": NOW - timedelta(days=20),
        "subscription_end_date": NOW + timedelta(days=10),
        "subscription_cancelled_at": NOW - timedelta(days=2),
        "subscription_discount_applied": True,
        "subscription_discount_end_date": NOW + timedelta(days=10),
        "created_at": NOW - timedelta(days=20),
        "updated_at": NOW - timedelta(days=2),
    },

    # ── Google OAuth user ─────────────────────────────────────────────────────
    {
        "email": "eve.oauth@gmail.com",
        "username": "eve_google",
        "first_name": "Eve",
        "last_name": "Martinez",
        "hashed_password": None,
        "profile_picture_url": "https://lh3.googleusercontent.com/a/placeholder",
        "is_active": True,
        "is_verified": True,   # Google accounts are pre-verified
        "auth_provider": "google",
        "google_id": "google_oauth_123456789",
        "credits": 3,
        "basic_credits": 3,
        "premium_credits": 0,
        "subscription_plan": "none",
        "subscription_status": "none",
        "created_at": NOW - timedelta(days=3),
        "updated_at": NOW - timedelta(days=3),
    },

    # ── Inactive / unverified account ─────────────────────────────────────────
    {
        "email": "frank@example.com",
        "username": "frank_unverified",
        "first_name": "Frank",
        "last_name": "Wilson",
        "hashed_password": hash_pw("Password123!"),
        "is_active": False,
        "is_verified": False,
        "auth_provider": "local",
        "credits": 3,
        "basic_credits": 3,
        "premium_credits": 0,
        "subscription_plan": "none",
        "subscription_status": "none",
        "created_at": NOW - timedelta(days=1),
        "updated_at": NOW - timedelta(days=1),
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def wipe_collection(col):
    result = await col.delete_many({})
    log.info(f"Wiped {result.deleted_count} existing user(s)")


async def seed(col, users: list[dict]) -> tuple[int, int]:
    inserted = skipped = 0
    for user in users:
        existing = await col.find_one({"email": user["email"]})
        if existing:
            log.info(f"  SKIP  {user['email']} (already exists)")
            skipped += 1
            continue
        # Remove None values so MongoDB doesn't store null for optional fields
        doc = {k: v for k, v in user.items() if v is not None}
        await col.insert_one(doc)
        log.info(f"  INSERT {user['email']}  [{user.get('subscription_plan','none')}]")
        inserted += 1
    return inserted, skipped


async def check(col):
    log.info(f"Users in '{MONGODB_DB}.{COLLECTION}':")
    async for u in col.find({}, {"email": 1, "username": 1, "subscription_plan": 1,
                                  "is_active": 1, "is_verified": 1, "_id": 0}):
        log.info(f"  {u}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main(wipe: bool, check_only: bool):
    client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
    try:
        await client.admin.command("ping")
        log.info(f"Connected to MongoDB: {MONGODB_URL}  db={MONGODB_DB}")
    except Exception as e:
        log.error(f"Cannot connect to MongoDB: {e}")
        sys.exit(1)

    col = client[MONGODB_DB][COLLECTION]

    if check_only:
        await check(col)
        client.close()
        return

    if wipe:
        await wipe_collection(col)

    inserted, skipped = await seed(col, SEED_USERS)
    log.info(f"\nDone — {inserted} inserted, {skipped} skipped")
    log.info("Seeded passwords (plain): Password123!  (admin: Admin@1234!)")
    client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed user profiles into MongoDB")
    parser.add_argument("--wipe",  action="store_true", help="Drop all users before seeding")
    parser.add_argument("--check", action="store_true", help="Print current users and exit")
    args = parser.parse_args()

    asyncio.run(main(wipe=args.wipe, check_only=args.check))
