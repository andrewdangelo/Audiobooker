"""
Clear all data from the database
"""
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.database import SessionLocal
from app.models.audiobook import Audiobook

def clear_database():
    """Delete all records from all tables"""
    db = SessionLocal()
    
    try:
        print("🗑️  Clearing database...")
        
        # Count records before deletion
        audiobook_count = db.query(Audiobook).count()
        print(f"   Found {audiobook_count} audiobook(s)")
        
        if audiobook_count == 0:
            print("✅ Database is already empty!")
            return True
        
        # Delete all audiobooks
        deleted = db.query(Audiobook).delete()
        db.commit()
        
        print(f"✅ Deleted {deleted} audiobook(s)")
        print("✅ Database cleared successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = clear_database()
    sys.exit(0 if success else 1)
