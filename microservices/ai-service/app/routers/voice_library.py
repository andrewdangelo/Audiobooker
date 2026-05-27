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

class VoiceDoc(BaseModel):
    voice_id: str
    original_filename: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    is_standard: bool = False

class ListVoicesResponse(BaseModel):
    total: int
    voices: List[VoiceDoc]

class AddVoiceResponse(BaseModel):
    voice_id: str

class DeleteVoiceResponse(BaseModel):
    deleted: bool
    voice_id: str

class DeleteAllVoicesResponse(BaseModel):
    deleted_count: int

class UpdateVoiceRequest(BaseModel):
    is_standard: bool

class UpdateVoiceResponse(BaseModel):
    voice_id: str
    is_standard: bool

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

@router.get("/voices", response_model=ListVoicesResponse)
async def list_voices(request: Request, standard_only: bool = False):
    """
    List all voices in the library.
    Pass ?standard_only=true to filter to narrator-eligible voices only.
    Embeddings are excluded from the response.
    """
    manager = _get_manager(request)
    query = {"is_standard": True} if standard_only else {}
    cursor = manager.collection.find(query, {"embedding": 0})
    docs = await cursor.to_list(length=1000)

    voices = [
        VoiceDoc(
            voice_id=str(doc["_id"]),
            original_filename=doc.get("original_filename"),
            description=doc.get("description"),
            duration=doc.get("duration"),
            is_standard=doc.get("is_standard", False),
        )
        for doc in docs
    ]
    return ListVoicesResponse(total=len(voices), voices=voices)


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


@router.patch("/voices/{voice_id}", response_model=UpdateVoiceResponse)
async def update_voice(voice_id: str, body: UpdateVoiceRequest, request: Request):
    """
    Update a voice's is_standard flag without re-uploading the audio.
    Useful for promoting an existing voice to narrator status or demoting it.
    """
    manager = _get_manager(request)
    result = await manager.collection.update_one(
        {"_id": voice_id},
        {"$set": {"is_standard": body.is_standard}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found.")

    return UpdateVoiceResponse(voice_id=voice_id, is_standard=body.is_standard)


@router.delete("/voices", response_model=DeleteAllVoicesResponse)
async def delete_all_voices(request: Request):
    """
    Delete every voice from MongoDB and R2.
    R2 deletions are best-effort — a storage failure won't abort the wipe.
    """
    manager = _get_manager(request)
    cursor = manager.collection.find({}, {"_id": 1})
    all_docs = await cursor.to_list(length=10000)

    deleted_count = 0
    for doc in all_docs:
        voice_id = str(doc["_id"])
        success = await manager.delete_voice_by_id(voice_id)
        if success:
            deleted_count += 1

    return DeleteAllVoicesResponse(deleted_count=deleted_count)


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