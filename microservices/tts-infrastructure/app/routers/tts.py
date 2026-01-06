from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse
from typing import Optional
import json
import uuid
from datetime import datetime

from app.models.tts_schemas import (
    TTSRequest,
    TTSBatchRequest,
    TTSResponse,
    TTSBatchResponse
)
from app.services.tts_services import TTSService, ElevenLabsTTSProvider, OpenAITTSProvider
from app.core.config_settings import settings  # Assuming you have settings with API keys

router = APIRouter()

# Initialize TTS service (#TODO add this setup to startup event)
tts_service = TTSService(output_dir="audio_output")

# Register providers
if hasattr(settings, 'ELEVENLABS_API_KEY') and settings.ELEVENLABS_API_KEY:
    tts_service.register_provider(
        "elevenlabs",
        ElevenLabsTTSProvider(api_key=settings.ELEVENLABS_API_KEY)
    )

if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
    tts_service.register_provider(
        "openai",
        OpenAITTSProvider(api_key=settings.OPENAI_API_KEY)
    )

@router.post("/generate", response_model=TTSResponse)
async def generate_tts(request: TTSRequest):
    """
    Generate TTS for a single chunk
    """
    try:
        audio_path, duration = await tts_service.generate_audio(chunk_id=request.chunk_id, text=request.text, provider_name=request.provider,
                                voice_id=request.voice_id, model_id=request.model_id, voice_settings=request.voice_settings)

        return TTSResponse(
            chunk_id=request.chunk_id,
            status="success",
            audio_path=audio_path,
            duration_seconds=duration
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch", response_model=TTSBatchResponse)
async def generate_batch_tts(request: TTSBatchRequest):
    """
    Generate TTS for multiple chunks from JSON file or direct data
    """
    try:
        # Load chunks
        if request.json_data:
            chunks = request.json_data
        elif request.json_file_path:
            with open(request.json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                chunks = data if isinstance(data, list) else data.get('chunks', [])
        else:
            raise HTTPException(
                status_code=400,
                detail="Either json_file_path or json_data must be provided"
            )
        
        # Process batch
        results = await tts_service.process_batch(chunks=chunks, provider_name=request.provider, voice_id=request.voice_id,
                                            model_id=request.model_id, voice_settings=request.voice_settings)
        
        # Convert results to response models
        tts_responses = [
            TTSResponse(
                chunk_id=r["chunk_id"],
                status=r["status"],
                audio_path=r["audio_path"],
                duration_seconds=r["duration_seconds"],
                error=r["error"]
            )
            for r in results
        ]
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        
        return TTSBatchResponse(
            batch_id=str(uuid.uuid4()),
            total_chunks=len(chunks),
            successful=successful,
            failed=failed,
            results=tts_responses
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-json", response_model=TTSBatchResponse)
async def upload_json_and_generate(file: UploadFile = File(...), provider: str = "elevenlabs", voice_id: Optional[str] = None, model_id: Optional[str] = None):
    """
    Upload a JSON file and generate TTS for all chunks
    """
    try:
        content = await file.read()
        data = json.loads(content)
        
        # Assumin that the data is a list or has a chunks key
        chunks = data if isinstance(data, list) else data.get('chunks', [])
        
        # Process batch
        results = await tts_service.process_batch(chunks=chunks, provider_name=provider, voice_id=voice_id, model_id=model_id)
        
        tts_responses = [
            TTSResponse(
                chunk_id=r["chunk_id"],
                status=r["status"],
                audio_path=r["audio_path"],
                duration_seconds=r["duration_seconds"],
                error=r["error"]
            )
            for r in results
        ]
        
        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "failed")
        
        return TTSBatchResponse(batch_id=str(uuid.uuid4()), total_chunks=len(chunks), successful=successful, failed=failed, results=tts_responses)
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio/{chunk_id}")
async def get_single_audio_from_chunk_id(chunk_id: str):
    """
    Download generated audio file by chunk_id.
    For example: Input: 1 ---> Should download audio from audio_output/1.mp3 
    """
    audio_path = f"audio_output/{chunk_id}.mp3"
    try:
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=f"{chunk_id}.mp3"
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Audio file not found")

@router.get("/voices/{provider}")
async def get_voices(provider: str = "elevenlabs"):
    """
    Get available voices for given provider.
    """
    try:
        voices = await tts_service.get_available_voices(provider_name=provider)
        return {"provider": provider, "voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/providers")
async def get_providers():
    """
    Get list of registered TTS providers
    """
    return {
        "providers": list(tts_service.providers.keys())
    }