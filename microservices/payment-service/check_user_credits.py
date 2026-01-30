from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to auth database
auth_url = os.getenv('AUTH_MONGODB_URL')
auth_db_name = os.getenv('AUTH_MONGODB_DB_NAME')
client = MongoClient(auth_url)
auth_db = client[auth_db_name]

# Get user document
user_id = '697cff8c537e94a7b0dc3047'
user = auth_db.users.find_one({'_id': user_id})

if user:
    print('=== USER DOCUMENT IN MONGODB ===')
    print(f'Database: {auth_db_name}')
    print(f'Collection: users')
    print(f'User ID: {user.get("_id")}')
    print(f'Email: {user.get("email")}')
    print()
    print('CREDIT FIELDS:')
    print(f'  credits (legacy): {user.get("credits", "FIELD MISSING")}')
    print(f'  basic_credits: {user.get("basic_credits", "FIELD MISSING")}')
    print(f'  premium_credits: {user.get("premium_credits", "FIELD MISSING")}')
    print()
    print('ALL FIELDS IN USER DOCUMENT:')
    for key in sorted(user.keys()):
        if key != 'password':
            print(f'  {key}: {user.get(key)}')
else:
    print(f'❌ User {user_id} not found in database')
