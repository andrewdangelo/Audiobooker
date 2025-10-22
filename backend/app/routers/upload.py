"""
Upload API Router
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
import uuid

router = APIRouter()


@router.post("/")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file for conversion - Simple test version
    
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
    
    # Validate file size (50MB)
    if file_size > 52428800:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of 50MB"
        )
    
    # Generate unique ID
    file_id = str(uuid.uuid4())
    
    # Just return success for now - testing file exchange
    return {
        "id": file_id,
        "filename": file.filename,
        "size": file_size,
        "message": "File received successfully!",
        "status": "pending"
    }


@router.get("/{upload_id}/status")
async def get_upload_status(upload_id: str):
    """Get the status of an upload/conversion"""
    return {
        "id": upload_id,
        "status": "pending",
        "message": "This is a test endpoint"
    }
