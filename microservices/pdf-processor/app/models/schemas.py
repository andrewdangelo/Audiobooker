"""
Pydantic Models and Schemas

Request/Response models for API endpoints.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class OutputFormat(str, Enum):
    """Supported output formats"""
    JSON = "json"
    TEXT = "text"
    MARKDOWN = "markdown"


class ProcessPDFRequest(BaseModel):
    """Request model for PDF processing"""
    r2_pdf_path: str = Field(..., description="R2 storage key for the PDF file", example="7e807a6e-f77d-4f9f-957e-9c395f1d3a8c/pdf/catcher.pdf")
    chunk_size: int = Field(default=1000, description="Size of text chunks in characters", ge=10, le=5000)
    chunk_overlap: int = Field(default=200, description="Overlap between chunks in characters", ge=0, le=1000)
    output_format: OutputFormat = Field(default=OutputFormat.JSON, description="Output format for processed text")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata to attach")
    
    @field_validator("r2_pdf_path")
    @classmethod
    def validate_r2_pdf_path(cls, v: str):
        """Validate R2 key format (PDF or EPUB)."""
        if not v or not v.strip():
            raise ValueError("r2_pdf_path cannot be empty")
        lower = v.strip().lower()
        if not (lower.endswith(".pdf") or lower.endswith(".epub")):
            raise ValueError("r2_pdf_path must end with .pdf or .epub")
        return v.strip()

    @model_validator(mode="after")
    def chunk_overlap_lt_size(self):
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        return self


class ProcessPDFResponse(BaseModel):
    """Response model for PDF processing request"""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    message: str = Field(..., description="Status message")
    r2_key: str = Field(..., description="R2 key of the PDF")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Job creation timestamp")


class JobStatusResponse(BaseModel):
    """Response model for job status"""
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Current status: pending, processing, completed, failed")
    progress: int = Field(..., description="Progress percentage (0-100)", ge=0, le=100)
    message: str = Field(..., description="Current status message")
    created_at: str = Field(..., description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")
    result: Optional[Dict[str, Any]] = Field(None, description="Processing results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    pipeline_stage: Optional[str] = Field(
        None,
        description="Unified pipeline stage for UI: pdf_processing, ai_enrichment, tts, backend_sync, completed, …",
    )
    audiobook_id: Optional[str] = Field(None, description="Backend library book id after successful sync")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="Service version")


class TextChunk(BaseModel):
    """Model for a text chunk"""
    chunk_id: int = Field(..., description="Chunk sequence number")
    text: str = Field(..., description="Chunk text content")
    page_numbers: List[int] = Field(..., description="Source page numbers")
    character_count: int = Field(..., description="Number of characters")
    start_char: int = Field(..., description="Starting character position in full text")
    end_char: int = Field(..., description="Ending character position in full text")
    chapter_id: Optional[int] = Field(default=None, description="Parent chapter ID")
    chapter_title: Optional[str] = Field(default=None, description="Parent chapter title")


class ChapterSchema(BaseModel):
    """Detected chapter structure"""
    chapter_id: int = Field(..., description="Sequential chapter number")
    title: str = Field(..., description="Chapter title")
    start_page: Optional[int] = Field(default=None, description="Starting page number")
    end_page: Optional[int] = Field(default=None, description="Ending page number")
    detection_method: str = Field(default="none", description="How the chapter was detected: toc, font, regex, llm, epub, none")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Detection confidence")


class ScriptSegment(BaseModel):
    """A speaker-attributed text segment in the multivoice script"""
    speaker: str = Field(..., description="Canonical speaker name")
    text: str = Field(..., description="Segment text content")
    chunk_id: Optional[int] = Field(default=None, description="Source chunk ID")
    is_quote: bool = Field(default=False, description="Whether this is dialogue")


class ScriptChapter(BaseModel):
    """A chapter in the multivoice script with attributed segments"""
    chapter_id: int = Field(..., description="Chapter number")
    title: str = Field(..., description="Chapter title")
    start_page: Optional[int] = Field(default=None)
    end_page: Optional[int] = Field(default=None)
    segments: List[ScriptSegment] = Field(default_factory=list)
    fidelity: Optional[Dict[str, Any]] = Field(default=None, description="Per-chapter fidelity report")


class PDFProcessingResult(BaseModel):
    """Complete PDF processing result"""
    r2_key: str = Field(..., description="Source PDF R2 key")
    total_pages: int = Field(..., description="Total number of pages")
    total_characters: int = Field(..., description="Total character count")
    total_chunks: int = Field(..., description="Total number of chunks")
    chunks: List[TextChunk] = Field(..., description="Text chunks")
    chapters: List[ChapterSchema] = Field(default_factory=list, description="Detected chapter structure")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="PDF metadata")
    processing_time: float = Field(..., description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Processing timestamp")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


class AudiobookDatabaseCreateRequest(BaseModel):
    """Create audiobook request"""
    r2_key: str
    user_id: str
    title: str
    pdf_path: Optional[str]
    status: str


class AudiobookDatabaseGetByIDRequest(BaseModel):
    """Get audiobook by ID request"""
    audiobook_id: str


class AudiobookDatabaseDeleteRequest(BaseModel):
    """Delete audiobook request"""
    audiobook_id: str