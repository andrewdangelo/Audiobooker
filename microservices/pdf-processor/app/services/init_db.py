"""
Initialize database tables
"""

import sys
from pathlib import Path

# Ensure project root is in Python path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database.database import Base, engine  # Adjust to your actual module paths
from app.models import audiobook       # Import all models here


def init_db():
    """Create all database tables"""
    print("Creating database tables...")
    print(f"Database URL: {engine.url}")

    try:
        # Create all tables if they don't exist
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")

        # List created tables
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f" - {table_name}")

        return True
    except Exception as e:
        print(f"Error creating tables: {e}")
        return False


if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
