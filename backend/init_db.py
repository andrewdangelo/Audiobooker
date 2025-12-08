"""
Initialize database tables
"""
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config.database import Base, engine
from app.models.audiobook import Audiobook  # Import all models

def init_db():
    """Create all database tables"""
    print("🔄 Creating database tables...")
    print(f"📊 Database URL: {engine.url}")
    
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        
        # List created tables
        print("\n📋 Created tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
