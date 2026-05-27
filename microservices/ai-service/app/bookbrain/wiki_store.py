"""
BookBrainWikiStore
==================
MongoDB-backed persistence layer for the BookBrain wiki.

Storage strategy
----------------
Primary:  MongoDB collection "bookbrain_wiki"
          - One document per (book_id, entry_type, title) tuple
          - Embedding stored inline for cosine-similarity retrieval
          - Good for structured queries, per-book scoping, and sub-second upserts

Optional: Cloudflare R2
          - Call export_markdown() and upload the result to
            bookbrain/{book_id}/wiki.md after a book is fully processed
          - Useful for human inspection and cross-service consumption
          - Not a substitute for Mongo: no vector search, no field-level queries

Scaling note
------------
The current similarity search loads ALL embeddings for a book into memory and
scores them with pure-Python cosine similarity.  That is fine up to ~5 000
entries per book (typical books: 200-600 entries).  When you hit production
scale, add a MongoDB Atlas Vector Search index on the `embedding` field and
replace `search_by_embedding` with a $vectorSearch aggregation pipeline —
zero schema changes required.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import List, Optional, Tuple

from motor.motor_asyncio import AsyncIOMotorCollection

from app.bookbrain.schemas import EntryType, WikiEntry, WikiEntryPublic

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def _doc_to_public(doc: dict) -> WikiEntryPublic:
    return WikiEntryPublic(**{k: v for k, v in doc.items() if k not in ("_id", "embedding")})


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------

class BookBrainWikiStore:
    """All DB operations for the BookBrain wiki."""

    COLLECTION_NAME = "bookbrain_wiki"

    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def upsert_entry(self, entry: WikiEntry) -> str:
        """
        Insert-or-update by (book_id, entry_type, case-insensitive title).
        On update: overwrites content, embedding, updated_at, and appends any
        new chunk indices — preserving the original entry_id and created_at.
        Returns the entry_id that was written.
        """
        now = datetime.utcnow()
        filter_ = {
            "book_id": entry.book_id,
            "entry_type": entry.entry_type,
            "title": {"$regex": f"^{entry.title}$", "$options": "i"},
        }
        update = {
            "$set": {
                "content": entry.content,
                "embedding": entry.embedding,
                "updated_at": now,
            },
            "$addToSet": {"source_chunk_indices": {"$each": entry.source_chunk_indices}},
            "$setOnInsert": {
                "entry_id": entry.entry_id,
                "book_id": entry.book_id,
                "entry_type": entry.entry_type,
                "title": entry.title,
                "created_at": now,
            },
        }
        await self.collection.update_one(filter_, update, upsert=True)
        return entry.entry_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_entries(
        self,
        book_id: str,
        entry_type: Optional[EntryType] = None,
    ) -> List[WikiEntryPublic]:
        """List all wiki entries for a book, embeddings excluded."""
        query: dict = {"book_id": book_id}
        if entry_type:
            query["entry_type"] = entry_type
        cursor = self.collection.find(query, {"embedding": 0})
        docs = await cursor.to_list(length=1000)
        return [_doc_to_public(d) for d in docs]

    async def get_narrative_cursor(self, book_id: str) -> Optional[WikiEntryPublic]:
        """
        Returns the current "Story So Far" summary — the running narrative cursor.

        This is the Karpathy-style index file: an auto-maintained entry that
        accumulates a chronological summary of everything that has happened in
        the book up to the most recently processed chunk.  It is always injected
        at the top of context before semantic retrieval, giving the LLM ordered
        narrative awareness on every subsequent chunk.

        Returns None before the first chunk is processed (wiki is empty).
        """
        doc = await self.collection.find_one(
            {
                "book_id": book_id,
                "entry_type": EntryType.SUMMARY,
                "title": {"$regex": r"^story so far$", "$options": "i"},
            },
            {"embedding": 0},
        )
        return _doc_to_public(doc) if doc else None

    async def search_by_embedding(
        self,
        book_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        entry_type: Optional[EntryType] = None,
        exclude_titles: Optional[List[str]] = None,
    ) -> List[Tuple[WikiEntryPublic, float]]:
        """
        Retrieve the top-k most relevant wiki entries via cosine similarity.

        exclude_titles: case-insensitive list of entry titles to skip — used to
        avoid double-injecting the "Story So Far" entry that is always added
        as the narrative cursor.

        Loads all embeddings for the book into memory (fast for ≤5 000 entries).
        For production at larger scale, swap this for an Atlas $vectorSearch query.
        """
        query: dict = {"book_id": book_id, "embedding": {"$exists": True, "$ne": None}}
        if entry_type:
            query["entry_type"] = entry_type

        docs = await self.collection.find(query).to_list(length=1000)
        if not docs:
            return []

        excluded = {t.lower() for t in (exclude_titles or [])}

        scored: List[Tuple[WikiEntryPublic, float]] = []
        for doc in docs:
            if doc.get("title", "").lower() in excluded:
                continue
            emb = doc.get("embedding")
            if not emb:
                continue
            score = _cosine(query_embedding, emb)
            scored.append((_doc_to_public(doc), score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    async def delete_book_wiki(self, book_id: str) -> int:
        """Delete all wiki entries for a book. Returns deleted count."""
        result = await self.collection.delete_many({"book_id": book_id})
        return result.deleted_count

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_markdown(self, book_id: str) -> str:
        """
        Render the full wiki as a single Markdown string, grouped by entry type.

        Upload this to R2 at bookbrain/{book_id}/wiki.md for human inspection
        or cross-service access.  Example with aioboto3:

            async with r2_session.client("s3", ...) as s3:
                await s3.put_object(
                    Bucket=bucket,
                    Key=f"bookbrain/{book_id}/wiki.md",
                    Body=md.encode(),
                    ContentType="text/markdown",
                )
        """
        entries = await self.get_entries(book_id)
        if not entries:
            return f"# BookBrain Wiki: {book_id}\n\n*No entries yet.*\n"

        sections: dict[str, list[WikiEntryPublic]] = {}
        for e in entries:
            sections.setdefault(e.entry_type, []).append(e)

        lines: list[str] = [f"# BookBrain Wiki: {book_id}\n"]
        for etype, elist in sections.items():
            lines.append(f"\n## {etype.capitalize()}\n")
            for e in elist:
                lines.append(f"\n### {e.title}\n")
                lines.append(e.content)
                lines.append(f"\n*Sources: chunks {sorted(e.source_chunk_indices)}*\n")

        return "\n".join(lines)
