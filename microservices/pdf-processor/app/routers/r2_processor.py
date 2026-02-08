"""
R2 Processor Router
"""
__author__ = "Mohammad Saifan"

from fastapi import APIRouter, HTTPException, Body, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any
from app.services.r2_service import R2Service

router = APIRouter()
r2 = R2Service()


@router.get("/download/{key:path}")
async def download_file(key: str, user_id: str = Query(..., description="User ID")):
    """Download a file from Cloudflare R2"""
    try:
        file_data = r2.download_file(key)
        return StreamingResponse(iter([file_data]), media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={key}"})
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found in R2")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/{key:path}")
async def upload_processed_data(key: str, user_id: str = Query(..., description="User ID"), payload: Dict[str, Any] = Body(..., example={"total_pages": 125, "total_chunks": 48, "text_chunks": ["chunk 1...", "chunk 2..."]})):
    """Upload processed JSON data to R2"""
    try:
        response = r2.upload_processed_data(key, payload)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/exists/{key:path}")
async def file_exists(key: str, user_id: str = Query(..., description="User ID")):
    """Check if a file exists in Cloudflare R2"""
    try:
        exists = r2.file_exists(key)
        return {"key": key, "exists": exists}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/{key:path}")
async def get_metadata(key: str, user_id: str = Query(..., description="User ID")):
    """Get file metadata from Cloudflare R2"""
    try:
        metadata = r2.get_file_metadata(key)
        if metadata is None:
            raise HTTPException(status_code=404, detail="File not found or metadata unavailable")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_file(key: str, user_id: str = Query(..., description="User ID")):
    """Delete a file from Cloudflare R2"""
    try:
        r2.delete_file(key)
        return {"key": key, "deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))