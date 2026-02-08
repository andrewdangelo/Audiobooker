"""
Initialize MongoDB collections and indexes
"""
__author__ = "Mohammad Saifan"

import sys
from pathlib import Path
import asyncio

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from pymongo import MongoClient
from app.core.config_settings import settings
from app.database.database import get_database, connect_to_mongodb, close_mongodb_connection
from app.models.db_models import Collections


async def create_indexes():
    """Create indexes for MongoDB collections"""
    db = get_database()
        
    try:
        # Audiobooks indexes
        db[Collections.AUDIOBOOKS].create_index("r2_key", unique=True)
        db[Collections.AUDIOBOOKS].create_index("user_id")
        db[Collections.AUDIOBOOKS].create_index("status")
        db[Collections.AUDIOBOOKS].create_index("title")
        
        # Processed Audiobooks indexes
        db[Collections.PROCESSED_AUDIOBOOKS].create_index("r2_key", unique=True)
        db[Collections.PROCESSED_AUDIOBOOKS].create_index("user_id")
        db[Collections.PROCESSED_AUDIOBOOKS].create_index("status")
        db[Collections.PROCESSED_AUDIOBOOKS].create_index("title")

        
        for collection_name in db.list_collection_names():
            print(f" - {collection_name}")
        
        return True
    except Exception as e:
        print(f"failed to create indexes: {e}")
        return False

def drop_all_collections():
    """Drop all collections"""
    print("=" * 60)
    print(f"Database: {settings.DATABASE_NAME}")
    print(f"URL: {settings.DATABASE_URL}")
    print("=" * 60)
    response = input("Type 'yes' to continue: ")
    
    if response.lower() == 'yes':
        try:
            # Create a fresh client connection
            client = MongoClient(settings.DATABASE_URL)
            db = client[settings.DATABASE_NAME]
            
            collection_names = db.list_collection_names()
            
            if not collection_names:
                print("No collections found to drop.")
                return True
            
            print(f"\nDropping {len(collection_names)} collections...")
            
            for collection_name in collection_names:
                db.drop_collection(collection_name)
                print(f"✓ Dropped collection: {collection_name}")
            
            # Verify all collections are gone
            remaining = db.list_collection_names()
            if remaining:
                print(f"\n⚠️  Warning: {len(remaining)} collections still exist:")
                for name in remaining:
                    print(f"  - {name}")
            else:
                print("\n✅ All collections dropped successfully!")
            
            client.close()
            return True
        except Exception as e:
            print(f"❌ Error dropping collections: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("Operation cancelled.")
        return False


def drop_entire_database():
    """Drop the entire database"""
    print("=" * 60)
    print(f"Database: {settings.DATABASE_NAME}")
    print(f"URL: {settings.DATABASE_URL}")
    print("=" * 60)
    response = input("Type 'DELETE DATABASE' to continue: ")
    
    if response == 'DELETE DATABASE':
        try:
            # Create a fresh client connection
            client = MongoClient(settings.DATABASE_URL)
            
            client.drop_database(settings.DATABASE_NAME)
            
            # List remaining databases to verify
            for db_name in client.list_database_names():
                print(f"  - {db_name}")
            
            client.close()
            return True
        except Exception as e:
            return False
    else:
        print("Operation cancelled.")
        return False

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB initialization utility")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all collections in the database (DESTRUCTIVE)"
    )
    parser.add_argument(
        "--drop-database",
        action="store_true",
        help="Drop the entire database (EXTREMELY DESTRUCTIVE)"
    )
    
    args = parser.parse_args()
    
    # Connect to MongoDB
    await connect_to_mongodb()
    
    if args.drop_database:
        # Drop entire database
        drop_entire_database()
    elif args.drop:
        # Drop all collections
        drop_all_collections()
    
    # Create indexes
    success = await create_indexes()
    
    # Close connection
    await close_mongodb_connection()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())