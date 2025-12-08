"""
Upload API Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
import uuid
import logging

from storage_sdk import R2Client
from storage_sdk.path_utils import generate_file_key, sanitize_filename
from config.database import get_db
from config.settings import settings
from app.services.audiobook_service import AudiobookService

logger = logging.getLogger(__name__)

# Initialize R2 client once (will be reused across requests)
r2_client = R2Client(
    account_id=settings.R2_ACCOUNT_ID,
    access_key_id=settings.R2_ACCESS_KEY_ID,
    secret_access_key=settings.R2_SECRET_ACCESS_KEY,
    bucket_name=settings.R2_BUCKET_NAME
)

router = APIRouter()


@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF file for conversion
    
    - **file**: PDF file to upload (max 50MB)
    
    Returns audiobook record with storage location
    """
    try:
        # Validate file extension
        if not file.filename or not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Validate filename is a string
        if not isinstance(file.filename, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid filename type: {type(file.filename).__name__}"
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
        
        # Generate unique book ID
        book_id = str(uuid.uuid4())
        
        # Sanitize filename and generate R2 key
        safe_filename = sanitize_filename(file.filename)
        r2_key = generate_file_key(
            book_id=book_id,
            file_type="pdf",
            file_name=safe_filename
        )
        
        # Upload to R2 using storage SDK
        logger.info(f"Uploading to R2: {r2_key}")
        upload_result = r2_client.upload(
            key=r2_key,
            file_data=content,
            content_type=file.content_type or "application/pdf"
        )
        
        # Create audiobook record in database
        logger.info(f"Creating database record")
        audiobook_service = AudiobookService(db)
        
        # Prepare data as dictionary for the service
        audiobook_data = {
            "id": book_id,
            "title": file.filename.rsplit('.', 1)[0],  # Remove .pdf extension
            "original_file_name": file.filename,
            "file_size": file_size,
            "pdf_path": upload_result["url"],  # r2://bucket/key format
            "status": "pending"
        }
        
        audiobook = audiobook_service.create(audiobook_data)
        
        logger.info(f"Upload complete - ID: {audiobook.id}")
        
        # Return audiobook details
        return {
            "id": str(audiobook.id),
            "title": audiobook.title,
            "filename": audiobook.original_file_name,
            "size": audiobook.file_size,
            "pdf_path": audiobook.pdf_path,
            "r2_key": upload_result["key"],  # Include R2 key for reference
            "r2_bucket": upload_result["bucket"],
            "status": audiobook.status,
            "created_at": audiobook.created_at.isoformat(),
            "message": "File uploaded successfully to R2 and database"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process upload: {str(e)}"
        )


@router.get("/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """Get the status of an upload/conversion"""
    return {
        "id": upload_id,
        "status": "pending",
        "message": "This is a test endpoint"
    }
