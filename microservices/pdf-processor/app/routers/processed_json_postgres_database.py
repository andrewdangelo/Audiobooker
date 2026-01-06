from fastapi import (APIRouter, Request)
import logging

from app.models.postgres_database_model import (AudiobookDatabaseCreateRequest, AudiobookDatabaseGetByIDRequest, AudiobookDatabaseDeleteRequest)
from app.database import (audio_book_db, database)
from app.models.audiobook import Processed_Audiobook

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/create")
async def create_processed_json_entry(audiobook_data: AudiobookDatabaseCreateRequest):
    """Create entry to DB"""
    
    db = connect_to_db()
    try:
        return db.create(dict(audiobook_data))
    except Exception as e:
        logger.error(f"Error creating entry in the Processed JSON PostgreSQL database: {e}")
        raise

@router.post("/get_by_id")
async def get_processed_json_by_id(audiobook_data: AudiobookDatabaseGetByIDRequest):
    """Get audiobook by ID"""
    
    db = connect_to_db()
    try:
        return db.get_by_id(audiobook_data.audiobook_id)
    except Exception as e:
        logger.error(f"Error getting audiobook by ID from Processed JSON PostgreSQL database: {e}")
        raise

@router.get("/get_all_audiobooks")
async def get_all_processed_json():
    """Get ALL audiobook"""
    
    db = connect_to_db()
    try:
        return db.get_all()
    except Exception as e:
        logger.error(f"Error getting ALL audiobook from Processed JSON PostgreSQL database: {e}")
        raise

@router.get("/count_of_audiobooks")
async def count_of_all_processed_json():
    """Get ALL audiobook"""
    
    db = connect_to_db()
    try:
        return db.count()
    except Exception as e:
        logger.error(f"Error getting count on ALL audiobook from Processed JSON PostgreSQL database: {e}")
        raise
        
@router.delete("/audiobook/{audiobook_id}")
async def delete_processed_json_by_id(audiobook_id: str):
    """Get ALL audiobook"""
    
    db = connect_to_db()
    try:
        return db.delete(audiobook_id)
    except Exception as e:
        logger.error(f"Error getting ALL audiobook from Processed JSON PostgreSQL database: {e}")
        raise

def connect_to_db():
    """Function to connect to the Processed JSON PostgreSQL database"""
    try:
        db_gen = database.get_db()
        db = next(db_gen)
        audiobook_service = audio_book_db.AudiobookDBService(db, model=Processed_Audiobook)
    except Exception as e:
        logger.error(f"Error connecting to the Processed JSON PostgreSQL database: {e}")
        raise
    
    return audiobook_service