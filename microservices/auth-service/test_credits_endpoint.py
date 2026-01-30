import requests
import os
import sys
sys.path.insert(0, 'app')
from core.security import create_access_token

# Create a token for the user
user_id = "697cff8c537e94a7b0dc3047"
token = create_access_token(data={"sub": user_id})

print(f'Testing credits endpoint for user: {user_id}')
print(f'Token: {token[:50]}...')
print()

# Test via API proxy
url = "http://localhost:8000/auth/accounts/credits"
headers = {"Authorization": f"Bearer {token}"}

print(f'GET {url}')
print(f'Headers: {headers}')
print()

response = requests.get(url, headers=headers)
print(f'Status: {response.status_code}')
print(f'Response: {response.json()}')
