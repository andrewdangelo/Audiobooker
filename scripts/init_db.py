#!/usr/bin/env python3
"""
Database initialization script
Creates all database tables
"""

import sys
from pathlib import Path

# ── Add backend directory to Python path ──────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent        # /Audiobooker
BACKEND_DIR = ROOT_DIR / "backend"                       # /Audiobooker/backend

sys.path.insert(0, str(BACKEND_DIR))

# Now these imports will work the same as inside backend/main.py
from config.database import Base, engine
from app.models.audiobook import Audiobook
from app.models.user import User
from app.models.conversion_job import ConversionJob
# ^ importing is enough to register them with Base.metadata

def init_db():
    """Initialize database tables"""
    print("🔄 Creating database tables...")
    print(f"📊 Database URL: {engine.url}")

    Base.metadata.create_all(bind=engine)

    print("✅ Database tables created successfully!")
    print("\n📋 Tables:")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")

if __name__ == "__main__":
    init_db()
