"""
BookBrain Schemas
=================
Pydantic models for the BookBrain wiki system.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class EntryType(str, Enum):
    CHARACTER = "character"
    THEME = "theme"
    SETTING = "setting"
    PLOT = "plot"
    TERMINOLOGY = "terminology"
    SUMMARY = "summary"


class WikiEntry(BaseModel):
    """Full wiki entry including embedding — used internally and for DB writes."""
    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    book_id: str
    entry_type: EntryType
    title: str
    content: str
    embedding: Optional[List[float]] = None
    source_chunk_indices: List[int] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WikiEntryPublic(BaseModel):
    """Wiki entry safe for API responses — embedding excluded."""
    entry_id: str
    book_id: str
    entry_type: EntryType
    title: str
    content: str
    source_chunk_indices: List[int]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestChunkRequest(BaseModel):
    chunk_text: str
    chunk_index: int
    book_title: Optional[str] = None
    total_chunks: Optional[int] = None  # pass when known; helps LLM understand narrative position


class IngestChunkResponse(BaseModel):
    book_id: str
    chunk_index: int
    retrieved_entries: int
    upserted_entries: int
    wiki_entry_ids: List[str]


class WikiSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    entry_type: Optional[EntryType] = None


class WikiSearchResponse(BaseModel):
    results: List[WikiEntryPublic]
    scores: List[float]


class WikiExportResponse(BaseModel):
    book_id: str
    markdown: str
    r2_key: Optional[str] = None


# ---------------------------------------------------------------------------
# Lint models — book knowledge base product
# ---------------------------------------------------------------------------

class LintGap(BaseModel):
    """One entry that was found to have missing fields and was enriched."""
    entry_id: str
    entry_type: EntryType
    title: str
    missing_fields: List[str]
    was_enriched: bool


class LintReport(BaseModel):
    """Result of one lint pass over a book's wiki."""
    book_id: str
    entries_checked: int
    entries_enriched: int
    gaps: List[LintGap]
    duration_seconds: float


# ---------------------------------------------------------------------------
# Bootstrap models — external-source seeding
# ---------------------------------------------------------------------------

class BootstrapRequest(BaseModel):
    """Seed the wiki from publicly available sources before ingestion begins."""
    book_title: str
    author: Optional[str] = None


class BootstrapReport(BaseModel):
    """Result of one bootstrap pass over external sources."""
    book_id: str
    book_title: str
    sources_queried: List[str]
    sources_succeeded: List[str]
    entries_seeded: int
    duration_seconds: float
