"""
Conversion API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from config.database import get_db
from app.schemas.conversion_job import ConversionJobResponse
from app.services.audiobook_service import AudiobookService

router = APIRouter()


@router.post("/{audiobook_id}/start")
async def start_conversion(
    audiobook_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start the PDF to audiobook conversion process
    
    - **audiobook_id**: ID of the audiobook to convert
    """
    # Check if audiobook exists
    audiobook_service = AudiobookService(db)
    audiobook = audiobook_service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    # TODO: Add conversion job to background tasks
    # background_tasks.add_task(conversion_service.convert, audiobook_id)
    
    return {
        "message": "Conversion started",
        "audiobook_id": audiobook_id,
        "status": "processing"
    }


@router.get("/{audiobook_id}/status")
async def get_conversion_status(
    audiobook_id: str,
    db: Session = Depends(get_db)
):
    """Get the conversion status of an audiobook"""
    audiobook_service = AudiobookService(db)
    audiobook = audiobook_service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    return {
        "audiobook_id": audiobook.id,
        "status": audiobook.status,
        "progress": 0,  # TODO: Calculate actual progress
        "message": f"Conversion is {audiobook.status}"
    }
