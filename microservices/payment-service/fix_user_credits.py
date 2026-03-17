from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to auth database
auth_url = os.getenv('AUTH_MONGODB_URL')
auth_db_name = os.getenv('AUTH_MONGODB_DB_NAME')
client = MongoClient(auth_url)
auth_db = client[auth_db_name]

# Update user to ensure basic_credits field exists
user_id = '697cff8c537e94a7b0dc3047'

print(f'Updating user {user_id}...')
result = auth_db.users.update_one(
    {'_id': ObjectId(user_id)},
    {'$set': {'basic_credits': 0}}
)

print(f'Modified: {result.modified_count}')

# Verify
user = auth_db.users.find_one({'_id': ObjectId(user_id)})
print()
print('Updated user document:')
print(f'  credits: {user.get("credits", "MISSING")}')
print(f'  basic_credits: {user.get("basic_credits", "MISSING")}')
print(f'  premium_credits: {user.get("premium_credits", "MISSING")}')
