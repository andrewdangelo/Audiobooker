"""
Upload API Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from sqlalchemy.orm import Session
import uuid
import logging

from config.database import get_db
from app.services.storage_service import StorageService
from app.services.audiobook_service import AudiobookService

logger = logging.getLogger(__name__)

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
        
        # Generate unique filename for storage
        file_id = str(uuid.uuid4())
        file_extension = file.filename.split('.')[-1]
        storage_filename = f"{file_id}.{file_extension}"
        
        # Upload to storage (R2 or local fallback)
        logger.info(f"Uploading to storage: {storage_filename}")
        storage_service = StorageService()
        file_path = await storage_service.upload_file(
            file_content=content,
            file_name=storage_filename,
            content_type=file.content_type or "application/pdf"
        )
        
        # Create audiobook record in database
        logger.info(f"Creating database record")
        audiobook_service = AudiobookService(db)
        
        # Prepare data as dictionary for the service
        audiobook_data = {
            "id": file_id,  # Use the same UUID we generated
            "title": file.filename.rsplit('.', 1)[0],  # Remove .pdf extension
            "original_file_name": file.filename,
            "file_size": file_size,
            "pdf_path": file_path,
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
            "status": audiobook.status,
            "created_at": audiobook.created_at.isoformat(),
            "message": "File uploaded successfully to storage and database"
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
