from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AudioFormat(str, Enum):
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"

class StitchRequest(BaseModel):
    chunk_ids: List[str] = Field(..., description="Ordered list of chunk IDs to stitch")
    crossfade_ms: Optional[int] = Field(0, ge=0, le=5000, description="Crossfade duration in milliseconds")
    normalize: bool = Field(True, description="Normalize audio levels across chunks")
    output_format: AudioFormat = Field(AudioFormat.MP3, description="Output audio format")
    output_filename: Optional[str] = Field(None, description="Custom output filename")

class StreamConfig(BaseModel):
    buffer_size: int = Field(4096, ge=1024, le=65536, description="Streaming buffer size in bytes")
    crossfade_ms: int = Field(0, ge=0, le=5000, description="Crossfade duration between chunks")
    bitrate: Optional[str] = Field("128k", description="Audio bitrate for streaming")

class AudioMetadata(BaseModel):
    duration_seconds: float
    format: str
    sample_rate: int
    channels: int
    bitrate: Optional[str] = None
    file_size_bytes: int

class ChunkInfo(BaseModel):
    chunk_id: str
    audio_path: str
    duration_seconds: Optional[float] = None
    status: Literal["pending", "loaded", "processed", "failed"] = "pending"
    error: Optional[str] = None

class StitchJob(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    chunks: List[ChunkInfo]
    total_chunks: int
    processed_chunks: int = 0
    total_duration_seconds: Optional[float] = None
    output_path: Optional[str] = None
    output_format: AudioFormat = AudioFormat.MP3
    crossfade_ms: int = 0
    normalize: bool = True
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class StitchResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    total_chunks: int
    estimated_duration_seconds: Optional[float] = None
    output_path: Optional[str] = None

class WebSocketMessage(BaseModel):
    type: Literal["metadata", "audio_chunk", "status", "error", "progress"]
    data: Optional[dict] = None
    message: Optional[str] = None

class StreamStartRequest(BaseModel):
    action: Literal["start", "pause", "resume", "stop"]
    job_id: str
    config: Optional[StreamConfig] = None

class StitchAndSaveRequest(BaseModel):
    chunk_ids: List[str]
    output_filename: str
    crossfade_ms: int = 0
    normalize: bool = True
    output_format: AudioFormat = AudioFormat.MP3

class StitchAndSaveResponse(BaseModel):
    job_id: str
    status: JobStatus
    output_path: str
    total_duration_seconds: float
    file_size_mb: float