#!/usr/bin/env python3
"""
Auth Service Verification and Startup Script

This script verifies that all components are properly configured,
then starts the auth service with detailed logging.
"""

import sys
import os
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_imports():
    """Verify all required imports work"""
    print("\n" + "="*60)
    print("STEP 1: Verifying Imports")
    print("="*60)
    
    try:
        print("✓ Importing fastapi...", end=" ")
        import fastapi
        print(f"v{fastapi.__version__}")
        
        print("✓ Importing uvicorn...", end=" ")
        import uvicorn
        print(f"v{uvicorn.__version__}")
        
        print("✓ Importing pydantic...", end=" ")
        import pydantic
        print(f"v{pydantic.__version__}")
        
        print("✓ Importing sqlalchemy...", end=" ")
        import sqlalchemy
        print(f"v{sqlalchemy.__version__}")
        
        print("✓ Importing app.core.config_settings...", end=" ")
        from app.core.config_settings import settings
        print("✓")
        
        print("✓ Importing app.database.database...", end=" ")
        from app.database.database import init_db, Base, engine
        print("✓")
        
        print("✓ Importing app.models.user...", end=" ")
        from app.models.user import User, AccountSettings, RefreshToken
        print("✓")
        
        print("✓ Importing app.services.auth_service...", end=" ")
        from app.services.auth_service import AuthService
        print("✓")
        
        print("✓ Importing app.routers...", end=" ")
        from app.routers import health, auth, accounts
        print("✓")
        
        print("\n✓ All imports successful!")
        return True
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}")
        return False


def verify_database():
    """Verify database setup"""
    print("\n" + "="*60)
    print("STEP 2: Verifying Database")
    print("="*60)
    
    try:
        from app.database.database import init_db
        from app.core.config_settings import settings
        
        print(f"Database URL: {settings.DATABASE_URL}")
        print("Initializing database...", end=" ")
        init_db()
        print("✓")
        
        print("Verifying tables...")
        from app.models.user import User, AccountSettings, RefreshToken
        from sqlalchemy import inspect, text
        from app.database.database import engine
        
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['user', 'account_settings', 'refresh_token']
        for table_name in required_tables:
            if table_name in tables:
                print(f"  ✓ {table_name}")
            else:
                print(f"  ✗ {table_name} NOT FOUND")
                return False
        
        print("\n✓ Database verified!")
        return True
        
    except Exception as e:
        print(f"\n✗ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_security():
    """Verify security utilities"""
    print("\n" + "="*60)
    print("STEP 3: Verifying Security Utilities")
    print("="*60)
    
    try:
        from app.utils.security import hash_password, verify_password, create_access_token, verify_token
        
        # Test password hashing
        print("Testing password hashing...", end=" ")
        test_pwd = "TestPassword123"
        hashed = hash_password(test_pwd)
        assert verify_password(test_pwd, hashed), "Password verification failed"
        print("✓")
        
        # Test JWT tokens
        print("Testing JWT token creation...", end=" ")
        token = create_access_token({"sub": "test@example.com"})
        payload = verify_token(token)
        assert payload["sub"] == "test@example.com", "Token payload mismatch"
        print("✓")
        
        print("\n✓ Security utilities verified!")
        return True
        
    except Exception as e:
        print(f"\n✗ Security verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_fastapi_app():
    """Verify FastAPI app initialization"""
    print("\n" + "="*60)
    print("STEP 4: Verifying FastAPI App")
    print("="*60)
    
    try:
        from main import app
        
        print(f"App title: {app.title}")
        print("Checking routes...")
        
        route_count = 0
        for route in app.routes:
            route_count += 1
            if hasattr(route, 'path'):
                print(f"  ✓ {route.methods if hasattr(route, 'methods') else 'N/A'} {route.path}")
        
        print(f"\nTotal routes: {route_count}")
        
        if route_count >= 15:
            print("\n✓ FastAPI app verified!")
            return True
        else:
            print(f"\n✗ Expected at least 15 routes, found {route_count}")
            return False
        
    except Exception as e:
        print(f"\n✗ FastAPI app verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_service():
    """Start the auth service"""
    print("\n" + "="*60)
    print("STEP 5: Starting Auth Service")
    print("="*60)
    
    try:
        import uvicorn
        from main import app
        from app.core.config_settings import settings
        
        print(f"\n🚀 Starting service on http://0.0.0.0:{settings.PORT}")
        print(f"📖 API Documentation: http://localhost:{settings.PORT}/docs")
        print(f"📚 ReDoc: http://localhost:{settings.PORT}/redoc")
        print("\nPress Ctrl+C to stop the service\n")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=settings.PORT,
            log_level="info"
        )
        
    except Exception as e:
        print(f"✗ Failed to start service: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all verifications"""
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*10 + "AUTH SERVICE VERIFICATION & STARTUP" + " "*14 + "║")
    print("╚" + "="*58 + "╝")
    
    checks = [
        ("Imports", verify_imports),
        ("Database", verify_database),
        ("Security", verify_security),
        ("FastAPI App", verify_fastapi_app),
    ]
    
    results = {}
    for name, check_fn in checks:
        try:
            results[name] = check_fn()
        except Exception as e:
            print(f"\n✗ {name} check failed with exception: {e}")
            results[name] = False
    
    # Print summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} - {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if all(results.values()):
        print("\n" + "="*60)
        print("✓ All checks passed! Starting service...\n")
        print("="*60)
        start_service()
    else:
        print("\n" + "="*60)
        print("✗ Some checks failed. Please fix the issues above.")
        print("="*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
