"""
Upload API Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from sqlalchemy.orm import Session
from config.database import get_db
from config.settings import settings
from app.services.storage_service import StorageService
from app.services.audiobook_service import AudiobookService
import uuid

router = APIRouter()


@router.post("/")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF file for conversion
    
    - **file**: PDF file to upload (max 50MB)
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are allowed"
        )
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file size
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
        )
    
    # Generate unique ID
    file_id = str(uuid.uuid4())
    
    # Upload to storage
    storage_service = StorageService()
    try:
        pdf_path = await storage_service.upload_file(
            file_content=content,
            file_name=f"{file_id}.pdf",
            content_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )
    
    # Create audiobook record
    audiobook_service = AudiobookService(db)
    audiobook = audiobook_service.create({
        "id": file_id,
        "title": file.filename.replace('.pdf', ''),
        "original_file_name": file.filename,
        "file_size": file_size,
        "pdf_path": pdf_path
    })
    
    return {
        "id": audiobook.id,
        "message": "File uploaded successfully",
        "status": "pending"
    }


@router.get("/{upload_id}/status")
async def get_upload_status(
    upload_id: str,
    db: Session = Depends(get_db)
):
    """Get the status of an upload/conversion"""
    audiobook_service = AudiobookService(db)
    audiobook = audiobook_service.get_by_id(upload_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found"
        )
    
    return {
        "id": audiobook.id,
        "status": audiobook.status,
        "title": audiobook.title
    }
