"""
Test script to manually add credits to a user
Run this to add credits if webhook didn't fire
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

async def add_credits_to_user(user_id: str, basic_credits: int = 0, premium_credits: int = 0):
    """Add credits to a user account"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(MONGO_URI)
    auth_db = client.auth_service
    
    try:
        # Update user credits
        result = await auth_db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {
                    "basic_credits": basic_credits,
                    "premium_credits": premium_credits,
                    "credits": basic_credits + premium_credits  # Legacy total
                },
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ Successfully added {basic_credits} basic credits and {premium_credits} premium credits to user {user_id}")
            
            # Fetch updated user to confirm
            user = await auth_db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                print(f"\nUpdated credits:")
                print(f"  Basic: {user.get('basic_credits', 0)}")
                print(f"  Premium: {user.get('premium_credits', 0)}")
                print(f"  Total: {user.get('credits', 0)}")
        else:
            print(f"❌ User {user_id} not found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

async def check_user_credits(user_id: str):
    """Check current credit balance"""
    client = AsyncIOMotorClient(MONGO_URI)
    auth_db = client.auth_service
    
    try:
        user = await auth_db.users.find_one({"_id": ObjectId(user_id)})
        if user:
            print(f"\nCurrent credits for user {user_id}:")
            print(f"  Email: {user.get('email')}")
            print(f"  Basic: {user.get('basic_credits', 0)}")
            print(f"  Premium: {user.get('premium_credits', 0)}")
            print(f"  Total: {user.get('credits', 0)}")
        else:
            print(f"❌ User {user_id} not found")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

async def check_recent_payments():
    """Check recent payment records"""
    client = AsyncIOMotorClient(MONGO_URI)
    payment_db = client.payment_service
    
    try:
        payments = await payment_db.payments.find().sort("created_at", -1).limit(5).to_list(length=5)
        
        print("\n📋 Recent payments:")
        for payment in payments:
            metadata = payment.get('metadata', {})
            print(f"\n  Payment ID: {payment.get('_id')}")
            print(f"  User ID: {payment.get('user_id')}")
            print(f"  Amount: ${payment.get('amount', 0) / 100:.2f}")
            print(f"  Status: {payment.get('status')}")
            print(f"  Credits: {metadata.get('credits', 0)}")
            print(f"  Credit Type: {metadata.get('credit_type', 'N/A')}")
            print(f"  Purchase Type: {metadata.get('purchase_type', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        client.close()

if __name__ == "__main__":
    import sys
    
    print("=== Credit Management Tool ===\n")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Check payments:  python test_add_credits.py payments")
        print("  Check credits:   python test_add_credits.py check <user_id>")
        print("  Add credits:     python test_add_credits.py add <user_id> <basic> <premium>")
        print("\nExample:")
        print("  python test_add_credits.py add 697cff8c537e94a7b0dc3047 3 0")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "payments":
        asyncio.run(check_recent_payments())
    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ Please provide user_id")
            sys.exit(1)
        user_id = sys.argv[2]
        asyncio.run(check_user_credits(user_id))
    elif command == "add":
        if len(sys.argv) < 5:
            print("❌ Please provide user_id, basic_credits, and premium_credits")
            sys.exit(1)
        user_id = sys.argv[2]
        basic = int(sys.argv[3])
        premium = int(sys.argv[4])
        asyncio.run(add_credits_to_user(user_id, basic, premium))
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)
