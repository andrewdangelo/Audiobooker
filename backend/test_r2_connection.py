"""
Quick test to verify R2 connection works
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.storage_service import StorageService
import asyncio

async def test_r2():
    print("🔍 Testing R2 connection...")
    
    # Initialize storage service
    storage = StorageService()
    
    if storage.use_local:
        print("❌ Using LOCAL storage (R2 not configured)")
        print(f"   Storage path: {storage.storage_path}")
        return False
    else:
        print(f"✅ Using CLOUDFLARE R2 storage")
        print(f"   Bucket: {storage.bucket_name}")
        print(f"   Endpoint: {storage.s3_client._endpoint}")
        
        # Try a simple test upload
        print("\n📤 Testing upload...")
        try:
            test_content = b"Hello from Audiobooker! R2 is working!"
            test_filename = "test-connection.txt"
            
            result = await storage.upload_file(
                file_content=test_content,
                file_name=test_filename,
                content_type="text/plain"
            )
            
            print(f"✅ Upload successful!")
            print(f"   File path: {result}")
            return True
            
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return False

if __name__ == "__main__":
    success = asyncio.run(test_r2())
    sys.exit(0 if success else 1)
