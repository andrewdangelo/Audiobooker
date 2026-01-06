from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class TTSRequest(BaseModel):
    chunk_id: str = Field(..., description="Unique identifier for the JSON chunk")
    text: str = Field(..., description="Text to convert to speech")
    provider: Literal["elevenlabs", "openai"] = Field(default="elevenlabs")
    voice_id: Optional[str] = Field(None, description="Voice ID for the TTS provider")
    model_id: Optional[str] = Field(None, description="Model ID (e.g., eleven_monolingual_v1)")
    voice_settings: Optional[dict] = Field(None, description="Voice settings like stability, similarity_boost")
    
class TTSBatchRequest(BaseModel):
    json_file_path: Optional[str] = Field(None, description="Path to JSON file with chunks")
    json_data: Optional[list[dict]] = Field(None, description="Direct JSON data with chunks")
    provider: Literal["elevenlabs", "openai"] = Field(default="elevenlabs")
    voice_id: Optional[str] = Field(None)
    model_id: Optional[str] = Field(None)
    voice_settings: Optional[dict] = Field(None)
    
class TTSResponse(BaseModel):
    chunk_id: str
    status: Literal["success", "failed", "processing"]
    audio_url: Optional[str] = None
    audio_path: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class TTSBatchResponse(BaseModel):
    batch_id: str
    total_chunks: int
    successful: int
    failed: int
    results: list[TTSResponse]
    
class ElevenLabsVoiceSettings(BaseModel):
    stability: float = Field(0.5, ge=0, le=1)
    similarity_boost: float = Field(0.75, ge=0, le=1)
    style: Optional[float] = Field(0, ge=0, le=1)
    use_speaker_boost: bool = Field(True)