"""
Processed JSON MongoDB Database Router
"""
__author__ = "Mohammad Saifan"

from fastapi import APIRouter, HTTPException, Query
import logging
from app.models.schemas import AudiobookDatabaseCreateRequest, AudiobookDatabaseGetByIDRequest, AudiobookDatabaseDeleteRequest
from app.database import database, db_engine
from app.models.db_models import Collections

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create")
async def create_processed_json_entry(user_id: str = Query(..., description="User ID"), audiobook_data: AudiobookDatabaseCreateRequest = None):
    """Create entry to MongoDB"""
    db = connect_to_db()
    try:
        data = dict(audiobook_data)
        data["user_id"] = user_id
        return db.create(data)
    except Exception as e:
        logger.error(f"Error creating entry in MongoDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get_by_id")
async def get_processed_json_by_id(user_id: str = Query(..., description="User ID"), audiobook_data: AudiobookDatabaseGetByIDRequest = None):
    """Get audiobook by ID"""
    db = connect_to_db()
    try:
        result = db.get_by_id(audiobook_data.audiobook_id)
        if not result:
            raise HTTPException(status_code=404, detail="Audiobook not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting audiobook by ID: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get_all_audiobooks")
async def get_all_processed_json(user_id: str = Query(..., description="User ID")):
    """Get ALL audiobooks"""
    db = connect_to_db()
    try:
        return db.get_all()
    except Exception as e:
        logger.error(f"Error getting all audiobooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count_of_audiobooks")
async def count_of_all_processed_json(user_id: str = Query(..., description="User ID")):
    """Get count of all audiobooks"""
    db = connect_to_db()
    try:
        return {"count": db.count()}
    except Exception as e:
        logger.error(f"Error counting audiobooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/audiobook/{audiobook_id}")
async def delete_processed_json_by_id(audiobook_id: str, user_id: str = Query(..., description="User ID")):
    """Delete audiobook by ID"""
    db = connect_to_db()
    try:
        deleted = db.delete(audiobook_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Audiobook not found")
        return {"deleted": True, "audiobook_id": audiobook_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting audiobook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def connect_to_db():
    """Function to connect to MongoDB"""
    try:
        db_gen = database.get_db()
        db = next(db_gen)
        return db_engine.MongoDBService(db, Collections.PROCESSED_AUDIOBOOKS)
    except Exception as e:
        logger.error(f"Error connecting to MongoDB: {e}")
        raise HTTPException(status_code=500, detail=str(e))