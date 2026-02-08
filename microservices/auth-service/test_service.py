"""
Test script for Auth Service
"""

import sys
import asyncio
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Test imports
print("=" * 60)
print("AUTH SERVICE - VERIFICATION TEST")
print("=" * 60)

try:
    print("\n1. Testing imports...")
    from app.core.config_settings import settings
    from app.database.database import engine, Base, init_db
    from app.models.user import User, AccountSettings, RefreshToken
    from app.services.auth_service import AuthService
    from app.services.account_service import AccountService
    from app.utils.security import hash_password, verify_password, create_access_token, verify_token
    from app.utils.google_oauth import google_oauth_manager
    from main import app
    print("✓ All imports successful")
    
    print("\n2. Testing configuration...")
    print(f"   Environment: {settings.ENVIRONMENT}")
    print(f"   Port: {settings.PORT}")
    print(f"   Database: {settings.DATABASE_URL}")
    print(f"   JWT Algorithm: {settings.ALGORITHM}")
    print(f"   Google OAuth: Enabled" if settings.GOOGLE_CLIENT_ID != "test-google-client-id" else "   Google OAuth: Not configured (placeholder)")
    print("✓ Configuration loaded")
    
    print("\n3. Testing database initialization...")
    init_db()
    print("✓ Database initialized")
    
    print("\n4. Testing password hashing...")
    test_password = "TestPass123"
    hashed = hash_password(test_password)
    is_valid = verify_password(test_password, hashed)
    assert is_valid, "Password verification failed"
    print(f"   Password: {test_password}")
    print(f"   Hashed: {hashed[:50]}...")
    print(f"   Verification: {'✓ PASS' if is_valid else '✗ FAIL'}")
    
    print("\n5. Testing JWT token creation...")
    access_token = create_access_token({"sub": "1"})
    payload = verify_token(access_token)
    assert payload is not None, "Token verification failed"
    assert payload.get("sub") == "1", "Token subject mismatch"
    print(f"   Access Token: {access_token[:50]}...")
    print(f"   Payload: {payload}")
    print("✓ JWT operations work correctly")
    
    print("\n6. Testing FastAPI app...")
    assert app is not None, "FastAPI app not initialized"
    print(f"   App Title: {app.title}")
    print(f"   App Version: {app.__version__}")
    print(f"   Routes: {len(app.routes)} routes registered")
    print("✓ FastAPI app initialized")
    
    print("\n7. Checking API endpoints...")
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append((route.path, route.methods))
    
    health_routes = [r for r in routes if "health" in r[0]]
    auth_routes = [r for r in routes if "auth" in r[0]]
    account_routes = [r for r in routes if "accounts" in r[0]]
    
    print(f"   Health endpoints: {len(health_routes)}")
    print(f"   Auth endpoints: {len(auth_routes)}")
    print(f"   Account endpoints: {len(account_routes)}")
    print("✓ Endpoints registered")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✓")
    print("=" * 60)
    print("\nService is ready to start!")
    print("\nTo start the service, run:")
    print("  python main.py")
    print("\nThen access the API at:")
    print("  http://localhost:8003")
    print("\nAPI Documentation:")
    print("  Swagger UI: http://localhost:8003/docs")
    print("  ReDoc: http://localhost:8003/redoc")
    
except Exception as e:
    print(f"\n✗ TEST FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
