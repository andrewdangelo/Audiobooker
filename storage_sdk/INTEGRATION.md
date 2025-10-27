# Storage SDK Integration Guide

## Quick Start

The `storage_sdk` is now available in the project. Here's how to use it in your code.

## For Backend (FastAPI)

### Update the Upload Router

Replace the current `StorageService` with the new SDK:

```python
# backend/app/routers/upload.py

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
import uuid
import logging
import sys
from pathlib import Path

# Add storage_sdk to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from storage_sdk import R2Client
from storage_sdk.path_utils import generate_file_key, sanitize_filename
from config.database import get_db
from app.services.audiobook_service import AudiobookService
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize R2 client once
r2_client = R2Client(
    account_id=os.getenv('R2_ACCOUNT_ID'),
    access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    bucket_name=os.getenv('R2_BUCKET_NAME')
)

@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        # Validate file
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Read file content
        logger.info(f"Processing upload: {file.filename}")
        content = await file.read()
        file_size = len(content)
        
        # Validate file size (50MB)
        if file_size > 52428800:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of 50MB"
            )
        
        # Generate unique book ID and R2 key
        book_id = str(uuid.uuid4())
        safe_filename = sanitize_filename(file.filename)
        
        r2_key = generate_file_key(
            book_id=book_id,
            file_type="pdf",
            file_name=safe_filename
        )
        
        # Upload to R2 using SDK
        logger.info(f"Uploading to R2: {r2_key}")
        upload_result = r2_client.upload(
            key=r2_key,
            file_data=content,
            content_type="application/pdf"
        )
        
        # Create audiobook record in database
        logger.info(f"Creating database record")
        audiobook_service = AudiobookService(db)
        
        audiobook_data = {
            "id": book_id,
            "title": file.filename.rsplit('.', 1)[0],
            "original_file_name": file.filename,
            "file_size": file_size,
            "pdf_path": upload_result["url"],  # r2://bucket/key format
            "status": "pending"
        }
        
        audiobook = audiobook_service.create(audiobook_data)
        
        logger.info(f"Upload complete - ID: {audiobook.id}")
        
        return {
            "id": str(audiobook.id),
            "title": audiobook.title,
            "filename": audiobook.original_file_name,
            "size": audiobook.file_size,
            "pdf_path": audiobook.pdf_path,
            "r2_key": upload_result["key"],
            "status": audiobook.status,
            "created_at": audiobook.created_at.isoformat(),
            "message": "File uploaded successfully to R2"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )
```

## For Processing Scripts

```python
# processing/convert_to_audio.py

import sys
from pathlib import Path
import os

# Add storage_sdk to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from storage_sdk import R2Client
from storage_sdk.path_utils import generate_file_key

# Initialize client
client = R2Client(
    account_id=os.getenv('R2_ACCOUNT_ID'),
    access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    bucket_name=os.getenv('R2_BUCKET_NAME')
)

def process_book(book_id: str, pdf_r2_key: str):
    """Download PDF, convert to audio, upload result"""
    
    # Download PDF from R2
    print(f"Downloading PDF: {pdf_r2_key}")
    pdf_bytes = client.download(key=pdf_r2_key)
    
    # Process the PDF (your conversion logic here)
    audio_bytes = convert_pdf_to_audio(pdf_bytes)
    
    # Generate R2 key for audio
    audio_key = generate_file_key(
        book_id=book_id,
        file_type="audio",
        file_name="audiobook.mp3"
    )
    
    # Upload audio to R2
    print(f"Uploading audio: {audio_key}")
    result = client.upload(
        key=audio_key,
        file_data=audio_bytes,
        content_type="audio/mpeg"
    )
    
    print(f"Processing complete!")
    print(f"Audio URL: {result['url']}")
    
    return result
```

## Environment Variables

Make sure these are set in your `.env` files:

```bash
# Backend .env
R2_ACCOUNT_ID=1049d9c736f1ba301b3a8c76ede09455
R2_ACCESS_KEY_ID=1d6d82ee3822ae2490bcb0b0b4759470
R2_SECRET_ACCESS_KEY=e491a96a668dea6fb464f6e68b7549e7b01e06d659cf30350aa95403b3183ec4
R2_BUCKET_NAME=audiobooker
```

## Testing the SDK

Run the example script to verify everything works:

```bash
cd storage_sdk
python example.py
```

This will test:
- ✅ Connection to R2
- ✅ File upload
- ✅ File download
- ✅ Presigned URLs
- ✅ File listing
- ✅ File deletion

## Benefits

1. **Cleaner Code** - Simple, clear API for R2 operations
2. **Reusable** - Same SDK works in backend, processing scripts, anywhere
3. **No Database Logic** - SDK only handles storage, returns data for you to save
4. **Consistent Paths** - Helper functions ensure organized file structure
5. **Good Errors** - Clear error messages for debugging

## Next Steps

1. Update `backend/app/routers/upload.py` to use the SDK
2. Remove old `backend/app/services/storage_service.py`
3. Update any processing scripts to use the SDK
4. Test uploads end-to-end
