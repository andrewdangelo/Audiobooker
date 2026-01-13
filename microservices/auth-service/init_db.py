"""
Database Initialization Script for Auth Service
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database.database import engine, Base, init_db
from app.models.user import User, AccountSettings, RefreshToken
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_tables():
    """Create all database tables"""
    try:
        init_db()
        logger.info("✓ All tables created successfully")
    except Exception as e:
        logger.error(f"✗ Error creating tables: {str(e)}")
        raise


def drop_tables():
    """Drop all database tables"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("✓ All tables dropped successfully")
    except Exception as e:
        logger.error(f"✗ Error dropping tables: {str(e)}")
        raise


def reset_database():
    """Reset database (drop and recreate)"""
    try:
        drop_tables()
        create_tables()
        logger.info("✓ Database reset successfully")
    except Exception as e:
        logger.error(f"✗ Error resetting database: {str(e)}")
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auth Service Database Management")
    parser.add_argument(
        "action",
        choices=["create", "drop", "reset"],
        help="Action to perform on database"
    )
    
    args = parser.parse_args()
    
    if args.action == "create":
        create_tables()
    elif args.action == "drop":
        drop_tables()
    elif args.action == "reset":
        reset_database()
