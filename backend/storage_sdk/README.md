# Cloudflare R2 Storage SDK

A lightweight Python library for interacting with Cloudflare R2 storage. Provides simple, consistent functions for uploading, downloading, deleting files, and generating presigned URLs.

## Features

- ✅ Upload files to R2 (from file path or bytes)
- ✅ Download files from R2 (to file or memory)
- ✅ Delete files from R2
- ✅ Generate presigned URLs (temporary upload/download links)
- ✅ List files in bucket with prefix filtering
- ✅ Consistent file path/key generation
- ✅ Clear error handling
- ✅ Simple API - no frameworks required

## Installation

### Prerequisites

The SDK requires `boto3` (AWS SDK for Python) to interact with R2's S3-compatible API.

```bash
pip install boto3
```

### Import in Your Project

Add the `storage_sdk` folder to your Python path, or place it in your project root:

```python
# If storage_sdk is in project root
from storage_sdk import R2Client, upload_file, download_file

# If storage_sdk is in a parent directory
import sys
sys.path.insert(0, '/path/to/storage_sdk')
from storage_sdk import R2Client
```

## Configuration

### R2 Credentials

You need the following from your Cloudflare R2 dashboard:

1. **Account ID** - Found in R2 dashboard
2. **Access Key ID** - From R2 API tokens
3. **Secret Access Key** - From R2 API tokens
4. **Bucket Name** - Your R2 bucket name

### Option 1: Environment Variables (Recommended)

Set these in your `.env` file or environment:

```bash
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
```

### Option 2: Direct Credentials

Pass credentials directly when creating the client:

```python
from storage_sdk import R2Client

client = R2Client(
    account_id="your_account_id",
    access_key_id="your_access_key_id",
    secret_access_key="your_secret_access_key",
    bucket_name="your_bucket_name"
)
```

## Usage Examples

### 1. Upload a File

#### Upload from File Path

```python
from storage_sdk import R2Client

# Initialize client
client = R2Client(
    account_id="your_account_id",
    access_key_id="your_access_key",
    secret_access_key="your_secret_key",
    bucket_name="audiobooker"
)

# Upload a PDF file
result = client.upload(
    key="user_123/book_456/document.pdf",
    file_path="/local/path/to/document.pdf",
    content_type="application/pdf"
)

print(result)
# {
#     "key": "user_123/book_456/document.pdf",
#     "bucket": "audiobooker",
#     "size": 1234567,
#     "url": "r2://audiobooker/user_123/book_456/document.pdf",
#     "content_type": "application/pdf",
#     "metadata": {}
# }
```

#### Upload Raw Bytes

```python
# Upload bytes directly
file_content = b"Hello, R2!"

result = client.upload(
    key="test/hello.txt",
    file_data=file_content,
    content_type="text/plain"
)
```

#### Quick Upload (Using Environment Variables)

```python
from storage_sdk import upload_file

# Uses R2_* environment variables automatically
result = upload_file(
    key="uploads/my-file.pdf",
    file_path="/local/file.pdf"
)
```

### 2. Download a File

#### Download to File

```python
# Download to local file
result = client.download(
    key="user_123/book_456/document.pdf",
    local_path="/downloads/document.pdf"
)

print(result)
# {
#     "key": "user_123/book_456/document.pdf",
#     "local_path": "/downloads/document.pdf",
#     "size": 1234567,
#     "content_type": "application/pdf",
#     "metadata": {}
# }
```

#### Download to Memory

```python
# Download as bytes
file_bytes = client.download(
    key="user_123/book_456/document.pdf"
)

# file_bytes is now a bytes object
print(len(file_bytes))  # File size in bytes
```

#### Quick Download (Using Environment Variables)

```python
from storage_sdk import download_file

# Download to file
result = download_file(
    key="uploads/my-file.pdf",
    local_path="/downloads/my-file.pdf"
)

# Or download to memory
file_bytes = download_file(key="uploads/my-file.pdf")
```

### 3. Delete a File

```python
# Delete a file from R2
result = client.delete(key="user_123/book_456/old-file.pdf")

print(result)
# {
#     "key": "user_123/book_456/old-file.pdf",
#     "bucket": "audiobooker",
#     "deleted": True
# }
```

#### Quick Delete

```python
from storage_sdk import delete_file

result = delete_file(key="uploads/unwanted.pdf")
```

### 4. Generate Presigned URLs

#### Download URL (GET)

```python
# Generate a temporary download link (valid for 1 hour)
result = client.generate_presigned_url(
    key="user_123/book_456/document.pdf",
    expiration=3600,  # 1 hour in seconds
    method="get"
)

print(result)
# {
#     "key": "user_123/book_456/document.pdf",
#     "url": "https://...presigned-url...",
#     "expires_in": 3600,
#     "method": "GET"
# }

# Share this URL with users for temporary download access
download_url = result["url"]
```

#### Upload URL (PUT)

```python
# Generate a temporary upload link
result = client.generate_presigned_url(
    key="user_123/book_456/new-upload.pdf",
    expiration=1800,  # 30 minutes
    method="put"
)

# Frontend can upload directly to this URL
upload_url = result["url"]
```

#### Quick Presigned URL

```python
from storage_sdk import generate_presigned_url

# Download URL
url_info = generate_presigned_url(
    key="uploads/file.pdf",
    expiration=3600
)

# Upload URL
url_info = generate_presigned_url(
    key="uploads/new-file.pdf",
    expiration=1800,
    method="put"
)
```

### 5. List Files

```python
# List all files in bucket
files = client.list_files()

for file in files:
    print(f"{file['key']} - {file['size']} bytes")
```

```python
# List files with prefix filter
files = client.list_files(
    prefix="user_123/",
    max_results=100
)

print(f"Found {len(files)} files for user_123")
```

### 6. Check if File Exists

```python
# Check if a file exists
exists = client.file_exists(key="user_123/book_456/document.pdf")

if exists:
    print("File exists in R2")
else:
    print("File not found")
```

### 7. Generate Consistent File Paths

```python
from storage_sdk import generate_file_key, generate_unique_key

# Generate organized path
key = generate_file_key(
    user_id="user_123",
    book_id="book_456",
    file_name="input.pdf"
)
# Result: "user_123/book_456/input.pdf"

# Generate path with file type folder
key = generate_file_key(
    book_id="book_789",
    file_type="audio",
    file_name="output.mp3"
)
# Result: "book_789/audio/output.mp3"

# Generate unique filename
key = generate_unique_key(
    prefix="audiobook",
    extension="pdf"
)
# Result: "audiobook_abc123-def456-789.pdf"
```

### 8. Parse File Paths

```python
from storage_sdk import parse_file_key

# Parse an R2 key
info = parse_file_key("user_123/book_456/document.pdf")

print(info)
# {
#     "full_key": "user_123/book_456/document.pdf",
#     "parts": ["user_123", "book_456", "document.pdf"],
#     "filename": "document.pdf",
#     "extension": "pdf",
#     "directory": "user_123/book_456",
#     "user_id": "user_123",
#     "book_id": "book_456"
# }
```

## Complete Examples

### Backend Upload Flow (FastAPI)

```python
from fastapi import FastAPI, UploadFile, File
from storage_sdk import R2Client
from storage_sdk.path_utils import generate_file_key, sanitize_filename
import uuid

app = FastAPI()

# Initialize R2 client (reads from env vars)
r2_client = R2Client(
    account_id=os.getenv("R2_ACCOUNT_ID"),
    access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    bucket_name=os.getenv("R2_BUCKET_NAME")
)

@app.post("/upload")
async def upload_book(file: UploadFile = File(...)):
    # Read file content
    content = await file.read()
    
    # Generate unique R2 key
    book_id = str(uuid.uuid4())
    safe_filename = sanitize_filename(file.filename)
    r2_key = generate_file_key(
        book_id=book_id,
        file_type="pdf",
        file_name=safe_filename
    )
    
    # Upload to R2
    result = r2_client.upload(
        key=r2_key,
        file_data=content,
        content_type=file.content_type
    )
    
    # Save result to database
    # db.save({
    #     "book_id": book_id,
    #     "r2_key": result["key"],
    #     "r2_url": result["url"],
    #     "file_size": result["size"]
    # })
    
    return {
        "book_id": book_id,
        "uploaded": True,
        "r2_key": result["key"],
        "size": result["size"]
    }
```

### Processing Script

```python
from storage_sdk import R2Client, download_file
import os

# Initialize client
client = R2Client(
    account_id=os.getenv("R2_ACCOUNT_ID"),
    access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
    secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
    bucket_name=os.getenv("R2_BUCKET_NAME")
)

# Download PDF from R2
pdf_key = "book_789/pdf/input.pdf"
pdf_bytes = client.download(key=pdf_key)

# Process the PDF
# ... your processing logic ...

# Upload result back to R2
audio_key = "book_789/audio/output.mp3"
client.upload(
    key=audio_key,
    file_data=processed_audio_bytes,
    content_type="audio/mpeg"
)

print(f"Processing complete! Audio at: {audio_key}")
```

### Cleanup Old Files

```python
from storage_sdk import R2Client
from datetime import datetime, timedelta

client = R2Client(...)

# List all files
files = client.list_files(prefix="temp/")

# Delete files older than 7 days
cutoff_date = datetime.now() - timedelta(days=7)

for file in files:
    if file["last_modified"] < cutoff_date:
        client.delete(key=file["key"])
        print(f"Deleted old file: {file['key']}")
```

## Error Handling

The SDK provides clear error messages:

```python
from storage_sdk import R2Client

client = R2Client(...)

try:
    # Try to download a non-existent file
    result = client.download(key="non-existent.pdf")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except Exception as e:
    print(f"Download failed: {e}")

try:
    # Try to upload with invalid credentials
    result = client.upload(key="test.pdf", file_path="/test.pdf")
except Exception as e:
    print(f"Upload failed (check credentials): {e}")
```

## API Reference

### R2Client Class

#### `__init__(account_id, access_key_id, secret_access_key, bucket_name, endpoint_url=None)`
Initialize the R2 client with credentials.

#### `upload(key, file_path=None, file_data=None, content_type=None, metadata=None)`
Upload a file to R2. Returns dict with upload details.

#### `download(key, local_path=None)`
Download a file from R2. Returns dict if local_path provided, bytes otherwise.

#### `delete(key)`
Delete a file from R2. Returns dict with deletion status.

#### `generate_presigned_url(key, expiration=3600, method="get")`
Generate a presigned URL. Returns dict with URL and expiration info.

#### `list_files(prefix=None, max_results=1000)`
List files in bucket. Returns list of file details.

#### `file_exists(key)`
Check if a file exists. Returns boolean.

### Convenience Functions

#### `upload_file(key, file_path=None, file_data=None, **kwargs)`
Quick upload using environment variables for credentials.

#### `download_file(key, local_path=None, **kwargs)`
Quick download using environment variables.

#### `delete_file(key, **kwargs)`
Quick delete using environment variables.

#### `generate_presigned_url(key, expiration=3600, method="get", **kwargs)`
Quick presigned URL using environment variables.

### Path Utilities

#### `generate_file_key(user_id=None, book_id=None, file_name=None, file_type=None, include_timestamp=False)`
Generate consistent R2 file keys.

#### `generate_unique_key(prefix="", extension="", separator="_")`
Generate unique file keys with UUID.

#### `parse_file_key(key)`
Parse an R2 key into components.

#### `sanitize_filename(filename)`
Sanitize filenames for safe storage.

#### `get_content_type(filename)`
Get MIME type from filename extension.

## Best Practices

1. **Use Environment Variables** - Keep credentials in `.env` files, never commit them
2. **Consistent Naming** - Use `generate_file_key()` for organized file paths
3. **Error Handling** - Always wrap R2 operations in try/except blocks
4. **Presigned URLs** - Use presigned URLs for direct frontend uploads/downloads
5. **Cleanup** - Periodically delete temporary or old files
6. **Content Types** - Always specify content_type for proper file serving

## Troubleshooting

### Connection Errors

**Problem:** `Failed to connect to R2`

**Solutions:**
- Verify R2 credentials are correct
- Check Account ID matches in both `R2_ACCOUNT_ID` and endpoint URL
- Ensure API token has "Object Read & Write" permissions
- Test credentials in Cloudflare dashboard

### File Not Found

**Problem:** `FileNotFoundError: File not found in R2`

**Solutions:**
- Verify the file key is correct (case-sensitive)
- Use `client.list_files()` to see what files exist
- Check if file was successfully uploaded

### Upload Fails

**Problem:** `R2 upload failed`

**Solutions:**
- Check file size limits (R2 supports files up to 5TB)
- Verify bucket name is correct
- Ensure API token has write permissions
- Check network connectivity

## License

This SDK is part of the Audiobooker project.

## Support

For issues or questions, please refer to the main project documentation or create an issue in the repository.
