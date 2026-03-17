from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to auth database
auth_url = os.getenv('AUTH_MONGODB_URL')
auth_db_name = os.getenv('AUTH_MONGODB_DB_NAME')

print(f'Connecting to: {auth_url}')
print(f'Database: {auth_db_name}')
print()

client = MongoClient(auth_url)
auth_db = client[auth_db_name]

# List all users
print('=== ALL USERS IN DATABASE ===')
users = list(auth_db.users.find({}, {'password': 0}))
print(f'Total users: {len(users)}')
print()

for i, user in enumerate(users, 1):
    print(f'{i}. User ID: {user.get("_id")}')
    print(f'   Email: {user.get("email")}')
    print(f'   credits: {user.get("credits", "MISSING")}')
    print(f'   basic_credits: {user.get("basic_credits", "MISSING")}')
    print(f'   premium_credits: {user.get("premium_credits", "MISSING")}')
    print()
