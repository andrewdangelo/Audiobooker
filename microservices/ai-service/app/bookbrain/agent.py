"""
BookBrain Agent
===============
Karpathy-style living-wiki builder for book text.

Design philosophy (Karpathy's own words):
  "raw data is collected, then compiled by an LLM into a .md wiki,
   then operated on by various CLIs by the LLM to do Q&A and to
   incrementally enhance the wiki. You rarely ever write or edit the
   wiki manually — it's the domain of the LLM."

Applied to book chunking:
  MongoDB      = the wiki storage substrate
  LLM          = the programmer that writes and maintains every entry
  chunk stream  = the raw/ directory being ingested in order
  bookbrain/   = the compiled wiki that grows with every commit (chunk)

Per-chunk agent loop
--------------------
1.  Embed the incoming chunk text
2a. Pull the narrative cursor ("Story So Far") — ALWAYS first, by title,
    regardless of semantic similarity.  This gives the LLM ordered context.
2b. Semantic search for top-k relevant wiki entries (excluding the cursor)
3.  Build context: [narrative cursor] then [semantic results]
4.  Call LLM with chunk position + context + chunk text
    → LLM MUST update "Story So Far" and MAY add/update other entries
5.  Embed + upsert all returned entries into MongoDB

The "Story So Far" entry is the Karpathy index file — a self-maintaining
chronological narrative that makes every subsequent chunk chunk-position-aware
without storing or re-reading prior raw text.

The agent is stateless — all state lives in BookBrainWikiStore.
"""
from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from app.bookbrain.schemas import EntryType, WikiEntry, WikiEntryPublic
from app.bookbrain.wiki_store import BookBrainWikiStore
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_model_factory import ModelProvider
from app.services.ai_text_service import AITextService

logger = logging.getLogger(__name__)

_NARRATIVE_CURSOR_TITLE = "Story So Far"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are the LLM programmer maintaining a growing wiki about a book.
Think of yourself as incrementally compiling a knowledge base — each chunk
of book text is a new commit to the codebase (the wiki).

CORE RULE — NARRATIVE CURSOR:
You MUST always output an entry with:
  entry_type = "summary"
  title      = "Story So Far"
This is the running narrative index. Update it to cover everything that has
happened chronologically through the current chunk, including new events.
Keep it under 500 words. Future chunks will receive this as their primary
ordered context — so accuracy and completeness matter.

WIKI RULES:
- You write and maintain ALL entries. They are never touched manually.
- Chunks arrive in order. Earlier chunk numbers happened before later ones.
- For existing entries: EXPAND or REFINE — never repeat verbatim content.
- For characters: capture speech patterns, relationships, aliases used in text,
  and which chunk they first appeared in.
- For plot entries: maintain chronological ordering of events.
- Cross-reference entries where relevant (e.g. "see also: Marcus Vane").
- Omit trivial details that add no analytical value.

Entry types (use exactly these strings):
  character | theme | setting | plot | terminology | summary

RESPONSE FORMAT — JSON only, no preamble, no markdown fences:
{
  "entries": [
    {
      "entry_type": "summary",
      "title": "Story So Far",
      "content": "<cumulative narrative through this chunk, ≤500 words>"
    },
    {
      "entry_type": "<type>",
      "title": "<short identifying title>",
      "content": "<1-3 paragraphs of markdown>"
    }
  ]
}
"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class BookBrainAgent:
    """
    Stateless agent wired to a BookBrainWikiStore.

    Default model choices:
      text  → chat-knowledge (gpt-oss-120b, 128k ctx) — best for literary analysis
      embed → embedding-768  (embeddinggemma-300m, CF) — matches voice_library pattern
    """

    def __init__(
        self,
        store: BookBrainWikiStore,
        text_provider: ModelProvider = ModelProvider.CF,
        text_preset: str = "chat-knowledge",
        emb_provider: ModelProvider = ModelProvider.CF,
        emb_preset: str = "embedding-768",
        retrieval_top_k: int = 5,
    ):
        self.store = store
        self._text_provider = text_provider
        self._text_preset = text_preset
        self._emb_provider = emb_provider
        self._emb_preset = emb_preset
        self._retrieval_top_k = retrieval_top_k

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    async def ingest_chunk(
        self,
        book_id: str,
        chunk_text: str,
        chunk_index: int,
        book_title: Optional[str] = None,
        total_chunks: Optional[int] = None,
    ) -> Tuple[List[str], int]:
        """
        Run the full agent loop for one book chunk.

        chunk_index must reflect the true position in the book (0-based).
        Pass total_chunks when known so the LLM understands where in the
        narrative it currently is.

        Returns:
            (upserted_entry_ids, retrieved_count)
        """
        # 1. Embed the chunk
        chunk_embedding = await AIEmbeddingService.generate_embedding(
            text=chunk_text,
            provider=self._emb_provider,
            preset=self._emb_preset,
        )

        # 2a. Narrative cursor — always retrieved first, by title.
        #     This is the ordered "what happened before this chunk" context.
        narrative_cursor = await self.store.get_narrative_cursor(book_id)

        # 2b. Semantic search — exclude the cursor so it isn't double-injected.
        retrieved = await self.store.search_by_embedding(
            book_id=book_id,
            query_embedding=chunk_embedding,
            top_k=self._retrieval_top_k,
            exclude_titles=[_NARRATIVE_CURSOR_TITLE],
        )
        retrieved_count = len(retrieved)

        # 3. Build context: narrative order first, then semantic relevance
        context_block = _build_context_block(narrative_cursor, retrieved)

        # 4. Construct user message with explicit chunk position
        position_line = _chunk_position_line(chunk_index, total_chunks)
        book_header   = f"**Book:** {book_title}\n" if book_title else ""

        user_message = (
            f"{book_header}"
            f"{position_line}\n\n"
            f"{context_block}"
            f"## Current Chunk Text\n\n"
            f"{chunk_text}\n\n"
            "Update the wiki. Remember to output the updated \"Story So Far\" entry."
        )

        raw = await AITextService.chat_with_system(
            system=_SYSTEM_PROMPT,
            user=user_message,
            provider=self._text_provider,
            preset=self._text_preset,
        )

        # 5. Parse, embed, and upsert each extracted entry
        parsed = _parse_entries(raw)
        upserted_ids: List[str] = []

        for item in parsed:
            entry_id = await self._upsert_item(book_id, chunk_index, item)
            if entry_id:
                upserted_ids.append(entry_id)

        # Warn if the LLM forgot the mandatory cursor entry
        titles_returned = {(item.get("title") or "").lower() for item in parsed}
        if _NARRATIVE_CURSOR_TITLE.lower() not in titles_returned:
            logger.warning(
                "BookBrain chunk %d [book=%s]: LLM did not return 'Story So Far' entry",
                chunk_index, book_id,
            )

        logger.info(
            "BookBrain chunk %d [book=%s]: cursor=%s retrieved=%d upserted=%d",
            chunk_index, book_id,
            "updated" if _NARRATIVE_CURSOR_TITLE.lower() in titles_returned else "MISSING",
            retrieved_count, len(upserted_ids),
        )
        return upserted_ids, retrieved_count

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _upsert_item(
        self,
        book_id: str,
        chunk_index: int,
        item: dict,
    ) -> Optional[str]:
        title          = (item.get("title") or "").strip()
        content        = (item.get("content") or "").strip()
        entry_type_raw = (item.get("entry_type") or "summary").strip().lower()

        if not title or not content:
            return None

        try:
            entry_type = EntryType(entry_type_raw)
        except ValueError:
            entry_type = EntryType.SUMMARY

        emb = await AIEmbeddingService.generate_embedding(
            text=f"{title}: {content}",
            provider=self._emb_provider,
            preset=self._emb_preset,
        )

        entry = WikiEntry(
            entry_id=str(uuid.uuid4()),
            book_id=book_id,
            entry_type=entry_type,
            title=title,
            content=content,
            embedding=emb,
            source_chunk_indices=[chunk_index],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        return await self.store.upsert_entry(entry)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _chunk_position_line(chunk_index: int, total_chunks: Optional[int]) -> str:
    if total_chunks:
        pct = round((chunk_index + 1) / total_chunks * 100)
        return f"**Position:** Chunk {chunk_index + 1} of {total_chunks} ({pct}% through the book)"
    return f"**Position:** Chunk {chunk_index + 1}"


def _build_context_block(
    narrative_cursor: Optional[WikiEntryPublic],
    semantic_results: list,
) -> str:
    """
    Build the context block that precedes the chunk text in the LLM prompt.

    Structure (Karpathy-ordered):
      1. Narrative cursor ("Story So Far") — always first, chronological anchor
      2. Semantically relevant wiki entries — by cosine similarity to this chunk
    """
    parts: list[str] = []

    # 1. Narrative cursor — ordered context
    if narrative_cursor:
        parts.append(
            "## Narrative Context (Story So Far)\n\n"
            f"{narrative_cursor.content}\n\n"
            f"*Covers chunks 0–{max(narrative_cursor.source_chunk_indices)}*"
        )
    else:
        parts.append(
            "## Narrative Context (Story So Far)\n\n"
            "*This is the first chunk — no prior narrative yet.*"
        )

    # 2. Semantic results — relevant wiki entries
    if semantic_results:
        semantic_parts = []
        for entry, score in semantic_results:
            semantic_parts.append(
                f"[{entry.entry_type.upper()}] **{entry.title}** "
                f"(relevance={score:.2f}, chunks={sorted(entry.source_chunk_indices)})\n"
                f"{entry.content}"
            )
        parts.append(
            "## Relevant Wiki Entries\n\n"
            + "\n\n---\n\n".join(semantic_parts)
        )

    return "\n\n".join(parts) + "\n\n"


def _parse_entries(raw: str) -> list[dict]:
    """
    Extract the entries list from LLM output.
    Handles: clean JSON, markdown-fenced JSON, and embedded JSON objects.
    """
    def _try(text: str) -> Optional[list]:
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data.get("entries", [])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    result = _try(raw)
    if result is not None:
        return result

    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if fenced:
        result = _try(fenced.group(1).strip())
        if result is not None:
            return result

    brace = re.search(r"\{[\s\S]*\}", raw)
    if brace:
        result = _try(brace.group(0))
        if result is not None:
            return result

    logger.warning("BookBrain: could not parse LLM output as JSON entries. Raw: %s", raw[:200])
    return []
