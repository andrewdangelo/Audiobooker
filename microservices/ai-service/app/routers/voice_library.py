"""
Voice Library Router

Exposes the VoiceLibraryManager to other microservices over HTTP.
All heavy lifting (audio processing, AI calls, storage) lives in the service layer.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel
from typing import Dict, List, Optional
import io

from app.services.voice_library import VoiceLibraryManager

router = APIRouter(prefix="/voice-library")


def _get_manager(request: Request) -> VoiceLibraryManager:
    manager: Optional[VoiceLibraryManager] = getattr(request.app.state, "voice_manager", None)
    if manager is None:
        raise RuntimeError("VoiceLibraryManager not initialised on app.state")
    return manager


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class AddVoiceResponse(BaseModel):
    voice_id: str

class DeleteVoiceResponse(BaseModel):
    deleted: bool
    voice_id: str

class AssignSingleRequest(BaseModel):
    quick: bool = True
    character: Optional[Dict] = None

class AssignSingleResponse(BaseModel):
    voice_id: str

class AssignMultipleRequest(BaseModel):
    characters: List[Dict]

class AssignMultipleResponse(BaseModel):
    assignments: Dict[str, str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/voices", response_model=AddVoiceResponse, status_code=201)
async def add_voice(
    request: Request,
    file: UploadFile = File(..., description="WAV audio file"),
    start_time: str = Form(default="00:00", description="Clip start offset MM:SS"),
    is_standard: bool = Form(default=False, description="Mark True to add to the safe narrator shortlist"),
):
    if not file.filename.endswith(".wav"):
        raise HTTPException(status_code=400, detail="Only .wav files are accepted.")

    raw_bytes = await file.read()
    audio_stream = io.BytesIO(raw_bytes)

    try:
        manager = _get_manager(request)
        voice_id = await manager.add_voice(
            input_audio=audio_stream,
            filename=file.filename,
            start_time=start_time,
            is_standard=is_standard,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AddVoiceResponse(voice_id=voice_id)


@router.delete("/voices/{voice_id}", response_model=DeleteVoiceResponse)
async def delete_voice(voice_id: str, request: Request):
    try:
        manager = _get_manager(request)
        deleted = await manager.delete_voice_by_id(voice_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found.")

    return DeleteVoiceResponse(deleted=True, voice_id=voice_id)


@router.post("/assign/single", response_model=AssignSingleResponse)
async def assign_voice_single(req: AssignSingleRequest, request: Request):
    if not req.quick and req.character is None:
        raise HTTPException(status_code=422, detail="character is required when quick=False")

    try:
        manager = _get_manager(request)
        voice_id = await manager.assign_voice_single(
            quick=req.quick,
            character=req.character,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AssignSingleResponse(voice_id=voice_id)


@router.post("/assign/multiple", response_model=AssignMultipleResponse)
async def assign_voice_multiple(req: AssignMultipleRequest, request: Request):
    if not req.characters:
        raise HTTPException(status_code=422, detail="characters list cannot be empty.")

    try:
        manager = _get_manager(request)
        assignments = await manager.assign_voice_multiple(req.characters)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AssignMultipleResponse(assignments=assignments)