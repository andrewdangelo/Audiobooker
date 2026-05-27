"""
BookBrain Router
================
REST API for the BookBrain living-wiki agent.

All endpoints are prefixed with /bookbrain (registered in main.py).

Routes
------
POST   /{book_id}/bootstrap       Seed wiki from external sources before ingestion (Tavily, Wikipedia, OpenLibrary, Gutenberg)
POST   /{book_id}/ingest          Process one chunk: retrieve context → extract entries → upsert wiki
GET    /{book_id}/wiki            List all wiki entries (optionally filtered by type)
POST   /{book_id}/wiki/search     Semantic search across a book's wiki
DELETE /{book_id}                 Delete all wiki entries for a book
GET    /{book_id}/export          Export full wiki as Markdown (uploadable to R2)
POST   /{book_id}/lint            Run enrichment pass — fills gaps in character profiles etc.
                                  Designed to run as a background job after ingestion completes.
                                  Powers the Audiobooker book knowledge base product.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.bookbrain.agent import BookBrainAgent
from app.bookbrain.bootstrap import BookBrainBootstrap
from app.bookbrain.linter import BookBrainLinter
from app.bookbrain.schemas import (
    BootstrapReport,
    BootstrapRequest,
    EntryType,
    IngestChunkRequest,
    IngestChunkResponse,
    LintReport,
    WikiExportResponse,
    WikiSearchRequest,
    WikiSearchResponse,
    WikiEntryPublic,
)
from app.core.config_settings import settings
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_model_factory import ModelProvider

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

def _get_agent(request: Request) -> BookBrainAgent:
    return request.app.state.bookbrain_agent


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{book_id}/ingest", response_model=IngestChunkResponse)
async def ingest_chunk(
    book_id: str,
    body: IngestChunkRequest,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    Run the BookBrain agent loop on a single book chunk.

    Steps (handled internally):
      1. Embed the chunk
      2. Retrieve relevant wiki entries from MongoDB
      3. Call the LLM with chunk + wiki context
      4. Parse and upsert new/updated wiki entries
    """
    if not body.chunk_text.strip():
        raise HTTPException(status_code=400, detail="chunk_text must not be empty")

    try:
        entry_ids, retrieved_count = await agent.ingest_chunk(
            book_id=book_id,
            chunk_text=body.chunk_text,
            chunk_index=body.chunk_index,
            book_title=body.book_title,
            total_chunks=body.total_chunks,
        )
    except Exception as e:
        logger.exception("BookBrain ingest failed book=%s chunk=%d", book_id, body.chunk_index)
        raise HTTPException(status_code=500, detail=str(e))

    return IngestChunkResponse(
        book_id=book_id,
        chunk_index=body.chunk_index,
        retrieved_entries=retrieved_count,
        upserted_entries=len(entry_ids),
        wiki_entry_ids=entry_ids,
    )


@router.get("/{book_id}/wiki", response_model=List[WikiEntryPublic])
async def get_wiki(
    book_id: str,
    entry_type: Optional[EntryType] = None,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    List all wiki entries for a book.
    Optionally filter by entry_type: character | theme | setting | plot | terminology | summary
    """
    return await agent.store.get_entries(book_id, entry_type)


@router.post("/{book_id}/wiki/search", response_model=WikiSearchResponse)
async def search_wiki(
    book_id: str,
    body: WikiSearchRequest,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    Semantic search across a book's wiki using embedding similarity.
    Returns top-k entries ranked by cosine similarity to the query.
    """
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="query must not be empty")

    try:
        query_emb = await AIEmbeddingService.generate_embedding(
            text=body.query,
            provider=ModelProvider.CF,
            preset="embedding-768",
        )
        results = await agent.store.search_by_embedding(
            book_id=book_id,
            query_embedding=query_emb,
            top_k=body.top_k,
            entry_type=body.entry_type,
        )
    except Exception as e:
        logger.exception("BookBrain search failed book=%s", book_id)
        raise HTTPException(status_code=500, detail=str(e))

    return WikiSearchResponse(
        results=[r[0] for r in results],
        scores=[r[1] for r in results],
    )


@router.delete("/{book_id}", status_code=204)
async def delete_book_wiki(
    book_id: str,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """Delete all wiki entries for a book. Irreversible."""
    deleted = await agent.store.delete_book_wiki(book_id)
    logger.info("BookBrain: deleted %d entries for book=%s", deleted, book_id)


@router.post("/{book_id}/lint", response_model=LintReport)
async def lint_wiki(
    book_id: str,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    Run a targeted enrichment pass over the book's wiki.

    For each entry the linter detects gaps using keyword heuristics, then
    fires a focused LLM call to fill only the missing fields:
      - character: speech_patterns, personality_traits, relationships, narrative_arc
      - plot:      characters_involved, consequence
      - theme:     textual_evidence

    Designed to run once after all chunks are ingested, or periodically.
    Powers the Audiobooker book knowledge base product — ensures every character
    has a fully enriched profile before it is surfaced to readers.

    For a 900-page book (~40 characters): expect 30-60s total.
    Wire to an ARQ background job for non-blocking use in production.
    """
    try:
        linter = BookBrainLinter(store=agent.store)
        report = await linter.lint(book_id)
    except Exception as e:
        logger.exception("BookBrain lint failed book=%s", book_id)
        raise HTTPException(status_code=500, detail=str(e))
    return report


@router.post("/{book_id}/bootstrap", response_model=BootstrapReport)
async def bootstrap_wiki(
    book_id: str,
    body: BootstrapRequest,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    Seed the book's wiki from external public sources before ingestion begins.

    Queries all 4 sources concurrently (~15-25s):
      - Tavily: 4 web searches (characters, themes, plot, literary analysis)
      - Wikipedia: REST API summary for the book's article
      - Open Library: work metadata (description, subjects, publish year)
      - Project Gutenberg: opening text + metadata for public domain books

    Any source that fails or returns nothing is silently skipped — the ingest
    loop is fully self-sufficient without bootstrap data.

    Designed to be triggered as a fire-and-forget parallel call from the
    pdf-processor immediately after a book job is created, before PDF extraction
    finishes. Wire to trigger_bookbrain_bootstrap() in pdf-processor/pipeline_client.py.

    Bootstrap entries are stored with source_chunk_index=-1 so the main ingest
    loop can distinguish and enrich them from the actual book text.
    """
    try:
        bootstrapper = BookBrainBootstrap(
            store=agent.store,
            tavily_api_key=settings.TAVILY_API_KEY,
        )
        report = await bootstrapper.bootstrap(
            book_id=book_id,
            book_title=body.book_title,
            author=body.author,
        )
    except Exception as e:
        logger.exception("BookBrain bootstrap failed book=%s", book_id)
        raise HTTPException(status_code=500, detail=str(e))
    return report


@router.get("/{book_id}/export", response_model=WikiExportResponse)
async def export_wiki_markdown(
    book_id: str,
    agent: BookBrainAgent = Depends(_get_agent),
):
    """
    Export the book's full wiki as a Markdown string.

    To persist to R2, take the returned `markdown` string and upload it:
        PUT bookbrain/{book_id}/wiki.md

    A future enhancement can wire this directly to R2 on the server side
    and return the r2_key in the response.
    """
    try:
        md = await agent.store.export_markdown(book_id)
    except Exception as e:
        logger.exception("BookBrain export failed book=%s", book_id)
        raise HTTPException(status_code=500, detail=str(e))

    return WikiExportResponse(book_id=book_id, markdown=md)
