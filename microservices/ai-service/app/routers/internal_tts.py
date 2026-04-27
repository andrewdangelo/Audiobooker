"""
Internal TTS Router
====================
Called by tts-infrastructure (and nothing else) to do the actual HF inference.
Keeps all model clients inside ai-service where HF credentials live.

Endpoint:
    POST /tts/generate-chunk  — voice sample + text → WAV bytes
    POST /voice-library/assign-single  — pick a random standard voice_id
"""

import base64
import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

from app.core.config_settings import settings
from app.services.ai_speech_service import AISpeechService

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

def _require_internal_key(x_internal_service_key: Optional[str]) -> None:
    if x_internal_service_key != settings.INTERNAL_SERVICE_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: invalid internal service key")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class GenerateChunkRequest(BaseModel):
    voice_sample_b64: str   # base64-encoded WAV bytes
    text: str
    emotion: str = "narrative, calm"
    emotion_strength: float = 0.5


class AssignVoiceRequest(BaseModel):
    quick: bool = True      # True = random standard voice (phase 1)


class AssignVoiceResponse(BaseModel):
    voice_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/tts/generate-chunk")
async def generate_chunk(
    request: GenerateChunkRequest,
    x_internal_service_key: Optional[str] = Header(None),
):
    """
    Generate speech for a single text chunk.
    Input:  base64 voice sample + text + optional emotion params
    Output: raw WAV bytes (audio/wav)
    """
    _require_internal_key(x_internal_service_key)

    try:
        voice_bytes = base64.b64decode(request.voice_sample_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 in voice_sample_b64")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    try:
        wav_bytes = await AISpeechService.generate_speech(
            voice_sample_bytes=voice_bytes,
            quote=request.text,
            emotion=request.emotion,
            emotion_strength=request.emotion_strength,
        )
    except Exception as e:
        logger.error("TTS inference failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS inference error: {e}")

    return Response(content=wav_bytes, media_type="audio/wav")


@router.post("/voice-library/assign-single", response_model=AssignVoiceResponse)
async def assign_voice_single(
    request: AssignVoiceRequest,
    req: Request,
    x_internal_service_key: Optional[str] = Header(None),
):
    """
    Pick a voice_id.
    quick=True (phase 1): random standard narrator voice from the library.
    """
    _require_internal_key(x_internal_service_key)

    voice_manager = req.app.state.voice_manager
    try:
        voice_id = await voice_manager.assign_voice_single(quick=request.quick)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Voice assignment failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Voice assignment error: {e}")

    return AssignVoiceResponse(voice_id=voice_id)