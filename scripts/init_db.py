#!/usr/bin/env python3
"""
Database initialization script
Creates all database tables
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.database import Base, engine
from app.models.audiobook import Audiobook
from app.models.user import User
from app.models.conversion_job import ConversionJob


def init_db():
    """Initialize database tables"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


if __name__ == "__main__":
    init_db()
