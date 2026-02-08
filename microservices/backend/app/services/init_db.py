"""
Initialize MongoDB collections and indexes
"""

__author__ = "Mohammad Saifan"

import sys
from pathlib import Path
import asyncio

# Ensure project root is in Python path
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
        # User Data indexes
        db[Collections.USER_DATA].create_index("id", unique=True)
        db[Collections.USER_DATA].create_index("email", unique=True)
        db[Collections.USER_DATA].create_index("role")
        
        # User Preferences indexes
        db[Collections.USER_PREFERENCES].create_index("id", unique=True)
        db[Collections.USER_PREFERENCES].create_index("user_id", unique=True)
        
        # User Credits indexes
        db[Collections.USER_CREDITS].create_index("id", unique=True)
        db[Collections.USER_CREDITS].create_index("user_id", unique=True)
        
        # User Stats indexes
        db[Collections.USER_STATS].create_index("id", unique=True)
        db[Collections.USER_STATS].create_index("user_id", unique=True)
        
        # Books indexes
        db[Collections.BOOKS].create_index("id", unique=True)
        db[Collections.BOOKS].create_index("title")
        db[Collections.BOOKS].create_index("author")
        db[Collections.BOOKS].create_index("genre")
        db[Collections.BOOKS].create_index("is_store_item")
        
        # Text index for search
        db[Collections.BOOKS].create_index([("title", "text"), ("author", "text")])
        
        # User Library indexes
        db[Collections.USER_LIBRARY].create_index("id", unique=True)
        db[Collections.USER_LIBRARY].create_index("user_id")
        db[Collections.USER_LIBRARY].create_index("book_id")
        db[Collections.USER_LIBRARY].create_index([("user_id", 1), ("book_id", 1)], unique=True)
        
        # User Activity indexes
        db[Collections.USER_ACTIVITY].create_index("id", unique=True)
        db[Collections.USER_ACTIVITY].create_index("user_id")
        db[Collections.USER_ACTIVITY].create_index("timestamp")
        
        # Cart Items indexes
        db[Collections.CART_ITEMS].create_index("id", unique=True)
        db[Collections.CART_ITEMS].create_index("user_id")
        db[Collections.CART_ITEMS].create_index("book_id")
        
        # Store Listings indexes
        db[Collections.STORE_LISTINGS].create_index("id", unique=True)
        db[Collections.STORE_LISTINGS].create_index("user_id")
        db[Collections.STORE_LISTINGS].create_index("book_id")
        db[Collections.STORE_LISTINGS].create_index("status")
        
        # Bookmarks indexes
        db[Collections.BOOKMARKS].create_index("id", unique=True)
        db[Collections.BOOKMARKS].create_index("user_id")
        db[Collections.BOOKMARKS].create_index("book_id")
        
        # Notifications indexes
        db[Collections.NOTIFICATIONS].create_index("id", unique=True)
        db[Collections.NOTIFICATIONS].create_index("user_id")
        db[Collections.NOTIFICATIONS].create_index("read")
         
        # List and print all collections
        for collection_name in db.list_collection_names():
            print(f" - [{collection_name}]")
        
        return True
    except Exception as e:
        print(f"Error creating indexes: {e}")
        return False


def drop_all_collections():
    """Drop all collections - USE WITH CAUTION"""
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
                print(f"\nWarning: {len(remaining)} collections still exist:")
                for name in remaining:
                    print(f"  - {name}")
            else:
                print("\nAll collections dropped successfully!")
            
            client.close()
            return True
        except Exception as e:
            print(f"Error dropping collections: {e}")
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
            
            print(f"\nDropping database '{settings.DATABASE_NAME}'...")
            client.drop_database(settings.DATABASE_NAME)
            print(f"Database '{settings.DATABASE_NAME}' has been completely deleted!")
            
            # List remaining databases to verify
            print("\nRemaining databases:")
            for db_name in client.list_database_names():
                print(f"  - {db_name}")
            
            client.close()
            return True
        except Exception as e:
            print(f"Error dropping database: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print("Operation cancelled.")
        return False


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="MongoDB initialization utility")
    parser.add_argument("--drop", action="store_true", help="Drop all collections in the database")
    parser.add_argument("--drop-database", action="store_true", help="Drop the entire database")
    
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