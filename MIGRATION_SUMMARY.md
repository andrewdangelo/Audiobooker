# Backend Storage SDK Migration Summary

## What Changed

The backend has been refactored to use the new **storage_sdk** instead of the old `StorageService`. This provides a cleaner, more consistent API for R2 operations.

## Files Modified

### 1. `backend/app/routers/upload.py` ✅
**Before:** Used `StorageService()` for uploads
**After:** Uses `storage_sdk.R2Client` with organized file paths

**Key Changes:**
- Replaced `StorageService` with `R2Client` from storage_sdk
- Added `generate_file_key()` for consistent file organization
- Added `sanitize_filename()` for safe filenames
- Files now stored in organized structure: `{book_id}/pdf/{filename}`
- Response includes `r2_key` and `r2_bucket` for reference

**Path Structure:**
```
Before: {uuid}.pdf
After:  {book_id}/pdf/{sanitized_filename}.pdf
```

### 2. `backend/app/routers/audiobooks.py` ✅
**New Features:**
- **Enhanced Delete:** Now deletes files from R2 before removing database record
- **PDF Download:** New endpoint `GET /{audiobook_id}/download` returns presigned URL
- **Audio Download:** New endpoint `GET /{audiobook_id}/audio/download` returns presigned URL

**New Endpoints:**

#### Get PDF Download URL
```bash
GET /api/v1/audiobooks/{audiobook_id}/download
```
Returns presigned URL valid for 1 hour:
```json
{
  "audiobook_id": "abc-123",
  "filename": "my-book.pdf",
  "download_url": "https://...presigned-url...",
  "expires_in": 3600,
  "message": "Use this URL to download the PDF (valid for 1 hour)"
}
```

#### Get Audio Download URL
```bash
GET /api/v1/audiobooks/{audiobook_id}/audio/download
```

#### Delete Audiobook (Enhanced)
```bash
DELETE /api/v1/audiobooks/{audiobook_id}
```
Now properly:
1. Deletes PDF from R2 (if exists)
2. Deletes audio from R2 (if exists)
3. Deletes database record
4. Returns 204 No Content on success

### 3. `backend/app/services/storage_service.py` ⚠️
**Status:** Deprecated but kept for backwards compatibility

The old `StorageService` is marked as deprecated and will be removed in a future version. All new code should use `storage_sdk` instead.

## Benefits

### ✅ Cleaner Code
```python
# Before
storage_service = StorageService()
file_path = await storage_service.upload_file(content, filename, content_type)

# After
upload_result = r2_client.upload(key=r2_key, file_data=content, content_type="application/pdf")
# Returns: {"key": "...", "bucket": "...", "size": 123, "url": "r2://..."}
```

### ✅ Organized File Structure
```python
# Consistent path generation
r2_key = generate_file_key(
    book_id=book_id,
    file_type="pdf",
    file_name=safe_filename
)
# Result: "book_123/pdf/My_Book.pdf"
```

### ✅ Proper File Cleanup
Delete operations now clean up both R2 storage and database:
```python
# Deletes PDF, audio, and database record
DELETE /api/v1/audiobooks/{id}
```

### ✅ Secure Downloads
Presigned URLs provide temporary, secure access without exposing credentials:
```python
# Generate 1-hour download link
presigned = r2_client.generate_presigned_url(key=pdf_key, expiration=3600)
```

### ✅ Better Error Handling
The SDK provides clear error messages and proper exception handling.

## Testing

### Test Upload
```bash
# Upload a PDF
curl -X POST http://localhost:8000/api/v1/upload/ \
  -F "file=@test.pdf"

# Response includes r2_key and organized path
{
  "id": "abc-123",
  "r2_key": "abc-123/pdf/test.pdf",
  "r2_bucket": "audiobooker",
  "pdf_path": "r2://audiobooker/abc-123/pdf/test.pdf"
}
```

### Test Download
```bash
# Get download URL
curl http://localhost:8000/api/v1/audiobooks/abc-123/download

# Response includes presigned URL
{
  "download_url": "https://...temporary-url...",
  "expires_in": 3600
}
```

### Test Delete
```bash
# Delete audiobook (removes from R2 and DB)
curl -X DELETE http://localhost:8000/api/v1/audiobooks/abc-123
```

## File Organization in R2

### Before
```
audiobooker/
  ├── a1b2c3d4.pdf
  ├── e5f6g7h8.pdf
  └── i9j0k1l2.pdf
```

### After
```
audiobooker/
  ├── book_abc123/
  │   ├── pdf/
  │   │   └── My_Book.pdf
  │   └── audio/
  │       └── audiobook.mp3
  ├── book_def456/
  │   └── pdf/
  │       └── Another_Book.pdf
  └── book_ghi789/
      └── pdf/
          └── Yet_Another_Book.pdf
```

## Migration Checklist

- [x] storage_sdk created with R2Client, path utilities, and documentation
- [x] upload.py refactored to use storage_sdk
- [x] audiobooks.py enhanced with download and delete using SDK
- [x] Old storage_service.py deprecated
- [x] All changes committed to feature/crud_service branch

## Next Steps

1. **Restart Backend** - The changes require a backend restart to take effect
   ```bash
   cd backend
   source venv/Scripts/activate
   python -m uvicorn main:app --reload
   ```

2. **Test Uploads** - Upload a PDF and verify the new path structure in R2

3. **Test Downloads** - Test the presigned URL endpoints

4. **Test Deletes** - Verify files are deleted from R2

5. **Update Processing Scripts** - When you create processing scripts, use the storage_sdk

6. **Merge to Master** - When ready, merge the feature branch:
   ```bash
   git checkout master
   git merge feature/crud_service
   git push origin master
   ```

## Example Processing Script (Future)

```python
from storage_sdk import R2Client
from storage_sdk.path_utils import generate_file_key
import os

# Initialize client
client = R2Client(
    account_id=os.getenv('R2_ACCOUNT_ID'),
    access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    bucket_name=os.getenv('R2_BUCKET_NAME')
)

# Download PDF
pdf_key = "book_123/pdf/My_Book.pdf"
pdf_bytes = client.download(key=pdf_key)

# Process PDF -> Audio
audio_bytes = convert_to_audio(pdf_bytes)

# Upload audio back to R2
audio_key = generate_file_key(
    book_id="book_123",
    file_type="audio",
    file_name="audiobook.mp3"
)
client.upload(key=audio_key, file_data=audio_bytes, content_type="audio/mpeg")
```

## Questions?

Refer to:
- `storage_sdk/README.md` - Full SDK documentation
- `storage_sdk/INTEGRATION.md` - Integration examples
- `storage_sdk/example.py` - Working example script
