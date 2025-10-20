"""
Audiobooks API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from config.database import get_db
from app.schemas.audiobook import AudiobookResponse, AudiobookListResponse, AudiobookUpdate
from app.services.audiobook_service import AudiobookService

router = APIRouter()


@router.get("/", response_model=AudiobookListResponse)
async def get_audiobooks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Get list of audiobooks
    
    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    service = AudiobookService(db)
    audiobooks = service.get_all(skip=skip, limit=limit)
    total = service.count()
    
    return {
        "items": audiobooks,
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit
    }


@router.get("/{audiobook_id}", response_model=AudiobookResponse)
async def get_audiobook(
    audiobook_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific audiobook by ID"""
    service = AudiobookService(db)
    audiobook = service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    return audiobook


@router.put("/{audiobook_id}", response_model=AudiobookResponse)
async def update_audiobook(
    audiobook_id: str,
    audiobook_update: AudiobookUpdate,
    db: Session = Depends(get_db)
):
    """Update an audiobook"""
    service = AudiobookService(db)
    audiobook = service.update(audiobook_id, audiobook_update)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    return audiobook


@router.delete("/{audiobook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audiobook(
    audiobook_id: str,
    db: Session = Depends(get_db)
):
    """Delete an audiobook"""
    service = AudiobookService(db)
    success = service.delete(audiobook_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    return None
