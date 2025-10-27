"""
Audiobooks API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import sys
import os
from pathlib import Path

# Add storage_sdk to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from storage_sdk import R2Client
from storage_sdk.path_utils import parse_file_key
from config.database import get_db
from app.schemas.audiobook import AudiobookResponse, AudiobookListResponse, AudiobookUpdate
from app.services.audiobook_service import AudiobookService

# Initialize R2 client
r2_client = R2Client(
    account_id=os.getenv('R2_ACCOUNT_ID'),
    access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    bucket_name=os.getenv('R2_BUCKET_NAME')
)

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
    """
    Delete an audiobook and its associated files from R2
    """
    service = AudiobookService(db)
    audiobook = service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    # Delete PDF from R2 if it exists
    if audiobook.pdf_path and audiobook.pdf_path.startswith('r2://'):
        try:
            # Extract R2 key from r2://bucket/key format
            parsed = parse_file_key(audiobook.pdf_path.replace('r2://', '').split('/', 1)[1])
            r2_client.delete(key=parsed['full_key'])
        except Exception as e:
            # Log but don't fail if file deletion fails
            print(f"Warning: Failed to delete PDF from R2: {e}")
    
    # Delete audio from R2 if it exists
    if audiobook.audio_path and audiobook.audio_path.startswith('r2://'):
        try:
            parsed = parse_file_key(audiobook.audio_path.replace('r2://', '').split('/', 1)[1])
            r2_client.delete(key=parsed['full_key'])
        except Exception as e:
            print(f"Warning: Failed to delete audio from R2: {e}")
    
    # Delete database record
    success = service.delete(audiobook_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete audiobook from database"
        )
    
    return None


@router.get("/{audiobook_id}/download")
async def download_audiobook_pdf(
    audiobook_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a presigned URL for downloading the audiobook PDF
    """
    service = AudiobookService(db)
    audiobook = service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    if not audiobook.pdf_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found for this audiobook"
        )
    
    # Generate presigned URL for download (valid for 1 hour)
    try:
        # Extract R2 key from r2://bucket/key format
        parsed = parse_file_key(audiobook.pdf_path.replace('r2://', '').split('/', 1)[1])
        
        presigned = r2_client.generate_presigned_url(
            key=parsed['full_key'],
            expiration=3600,  # 1 hour
            method="get"
        )
        
        return {
            "audiobook_id": audiobook_id,
            "filename": audiobook.original_file_name,
            "download_url": presigned["url"],
            "expires_in": presigned["expires_in"],
            "message": "Use this URL to download the PDF (valid for 1 hour)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )


@router.get("/{audiobook_id}/audio/download")
async def download_audiobook_audio(
    audiobook_id: str,
    db: Session = Depends(get_db)
):
    """
    Generate a presigned URL for downloading the audiobook audio file
    """
    service = AudiobookService(db)
    audiobook = service.get_by_id(audiobook_id)
    
    if not audiobook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audiobook not found"
        )
    
    if not audiobook.audio_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not available for this audiobook"
        )
    
    # Generate presigned URL for download (valid for 1 hour)
    try:
        # Extract R2 key from r2://bucket/key format
        parsed = parse_file_key(audiobook.audio_path.replace('r2://', '').split('/', 1)[1])
        
        presigned = r2_client.generate_presigned_url(
            key=parsed['full_key'],
            expiration=3600,  # 1 hour
            method="get"
        )
        
        return {
            "audiobook_id": audiobook_id,
            "download_url": presigned["url"],
            "expires_in": presigned["expires_in"],
            "message": "Use this URL to download the audio (valid for 1 hour)"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )
