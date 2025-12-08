"""
Example Usage of R2 Storage SDK

This script demonstrates all the main features of the storage SDK.
Make sure to set your R2 credentials in environment variables first.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path if running from storage_sdk folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage_sdk import (
    R2Client,
    generate_file_key,
    generate_unique_key,
    parse_file_key,
    sanitize_filename
)


def main():
    """Run example operations"""
    
    print("=" * 60)
    print("R2 Storage SDK - Example Usage")
    print("=" * 60)
    
    # Initialize client
    print("\n1️⃣  Initializing R2 Client...")
    try:
        client = R2Client(
            account_id=os.getenv('R2_ACCOUNT_ID'),
            access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
            secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
            bucket_name=os.getenv('R2_BUCKET_NAME')
        )
        print(f"   ✅ Connected to bucket: {client.bucket_name}")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        print("\n   Make sure you set these environment variables:")
        print("   - R2_ACCOUNT_ID")
        print("   - R2_ACCESS_KEY_ID")
        print("   - R2_SECRET_ACCESS_KEY")
        print("   - R2_BUCKET_NAME")
        return
    
    # Generate file keys
    print("\n2️⃣  Generating File Keys...")
    
    key1 = generate_file_key(
        user_id="user_123",
        book_id="book_456",
        file_name="example.pdf"
    )
    print(f"   📝 Organized key: {key1}")
    
    key2 = generate_unique_key(prefix="test", extension="txt")
    print(f"   📝 Unique key: {key2}")
    
    # Upload a test file
    print("\n3️⃣  Uploading Test File...")
    
    test_content = b"Hello from R2 Storage SDK! This is a test file."
    test_key = "sdk-examples/test-upload.txt"
    
    try:
        result = client.upload(
            key=test_key,
            file_data=test_content,
            content_type="text/plain",
            metadata={"source": "example_script"}
        )
        print(f"   ✅ Uploaded: {result['key']}")
        print(f"   📦 Size: {result['size']} bytes")
        print(f"   🔗 URL: {result['url']}")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return
    
    # Check if file exists
    print("\n4️⃣  Checking File Existence...")
    exists = client.file_exists(test_key)
    print(f"   {'✅' if exists else '❌'} File exists: {exists}")
    
    # Download the file
    print("\n5️⃣  Downloading File...")
    try:
        downloaded_content = client.download(key=test_key)
        print(f"   ✅ Downloaded {len(downloaded_content)} bytes")
        print(f"   📄 Content: {downloaded_content.decode()[:50]}...")
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
    
    # Generate presigned URL
    print("\n6️⃣  Generating Presigned URLs...")
    try:
        # Download URL (valid for 1 hour)
        download_url = client.generate_presigned_url(
            key=test_key,
            expiration=3600,
            method="get"
        )
        print(f"   ✅ Download URL (expires in {download_url['expires_in']}s)")
        print(f"   🔗 {download_url['url'][:80]}...")
        
        # Upload URL (valid for 30 minutes)
        upload_url = client.generate_presigned_url(
            key="sdk-examples/presigned-upload.txt",
            expiration=1800,
            method="put"
        )
        print(f"   ✅ Upload URL (expires in {upload_url['expires_in']}s)")
        print(f"   🔗 {upload_url['url'][:80]}...")
    except Exception as e:
        print(f"   ❌ Presigned URL failed: {e}")
    
    # List files
    print("\n7️⃣  Listing Files...")
    try:
        files = client.list_files(prefix="sdk-examples/", max_results=10)
        print(f"   📋 Found {len(files)} file(s) in sdk-examples/")
        for file in files[:5]:  # Show first 5
            print(f"      - {file['key']} ({file['size']} bytes)")
    except Exception as e:
        print(f"   ❌ List failed: {e}")
    
    # Parse file key
    print("\n8️⃣  Parsing File Key...")
    parsed = parse_file_key("user_123/book_456/document.pdf")
    print(f"   📝 Full key: {parsed['full_key']}")
    print(f"   📁 Directory: {parsed['directory']}")
    print(f"   📄 Filename: {parsed['filename']}")
    print(f"   🔖 Extension: {parsed['extension']}")
    print(f"   👤 User ID: {parsed['user_id']}")
    print(f"   📚 Book ID: {parsed['book_id']}")
    
    # Sanitize filename
    print("\n9️⃣  Sanitizing Filename...")
    unsafe_name = "My Book (2024) - Final Version!.pdf"
    safe_name = sanitize_filename(unsafe_name)
    print(f"   ❌ Unsafe: {unsafe_name}")
    print(f"   ✅ Safe: {safe_name}")
    
    # Delete the test file
    print("\n🔟 Deleting Test File...")
    try:
        result = client.delete(key=test_key)
        print(f"   ✅ Deleted: {result['key']}")
    except Exception as e:
        print(f"   ❌ Delete failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Example Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
