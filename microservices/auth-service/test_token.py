"""
Test token generation and verification
"""
import sys
sys.path.insert(0, 'app')

from app.utils.security import create_access_token, verify_token
from app.core.config_settings import settings

# Create a token for the test user
user_id = "697cff8c537e94a7b0dc3047"
token = create_access_token(data={"sub": user_id})

print("=== TOKEN TEST ===")
print(f"SECRET_KEY: {settings.SECRET_KEY}")
print(f"ALGORITHM: {settings.ALGORITHM}")
print()
print(f"Generated token for user {user_id}:")
print(token)
print()

# Verify the token
payload = verify_token(token)
print(f"Verification result: {payload}")
print()

if payload:
    print("✅ Token verification SUCCESSFUL")
    print(f"User ID from token: {payload.get('sub')}")
else:
    print("❌ Token verification FAILED")
