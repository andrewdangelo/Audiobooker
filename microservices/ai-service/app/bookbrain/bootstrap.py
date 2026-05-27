"""
BookBrainBootstrap
==================
Pre-ingestion seeding pass: queries 4 external sources in parallel, then
compiles the gathered info into structured wiki seed entries.

Sources
-------
  Tavily          — 4 concurrent web searches (characters, themes, plot, analysis)
  Wikipedia       — REST summary API (free, no key)
  Open Library    — work metadata (description, subjects, genres, publish year)
  Gutenberg       — plaintext snippet via gutendex.com for public domain books

Design
------
All 4 sources are queried concurrently via asyncio.gather. Any source that
fails or returns nothing is silently skipped — the system does NOT depend on
bootstrap data to function. If no sources return useful data, the report
records zero entries seeded and the main ingestion loop handles everything
from the raw book text alone.

After gathering raw text, one LLM call compiles it into structured wiki seed
entries (character stubs, theme stubs, setting notes). These are embedded and
upserted with source_chunk_index=-1 to mark bootstrap origin, so the ingest
loop enriches them rather than treating them as duplicates.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import httpx

from app.bookbrain.schemas import BootstrapReport, EntryType, WikiEntry
from app.bookbrain.wiki_store import BookBrainWikiStore
from app.services.ai_emb_service import AIEmbeddingService
from app.services.ai_model_factory import ModelProvider
from app.services.ai_text_service import AITextService

logger = logging.getLogger(__name__)

# sentinel: seeded before ingestion, not from a real chunk
_BOOTSTRAP_CHUNK_INDEX = -1

_TAVILY_URL = "https://api.tavily.com/search"
_WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
_OPENLIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
_GUTENDEX_URL = "https://gutendex.com/books/"

_TAVILY_QUERIES = [
    "{title} {author} main characters list",
    "{title} {author} themes and symbols",
    "{title} {author} plot summary",
    "{title} {author} literary analysis",
]

_COMPILE_SYSTEM = """\
You are a literary analyst seeding a book wiki from publicly available information.

Given raw text collected from multiple internet sources about a book, extract
structured wiki entries: character stubs, major themes, notable settings, and
key plot points (if clearly established by the sources).

IMPORTANT CONSTRAINTS:
- Only include facts well-established across the sources.
- Mark uncertainty with "reportedly" or "commonly described as" when unsure.
- Do NOT invent details not supported by the source text.
- Keep character entries concise — they will be enriched from the actual book text later.
- Skip spoilers unless they appear explicitly in all sources.
- Use only these entry_type values: character | theme | setting | plot | terminology

Respond ONLY with JSON, no preamble, no markdown fences:
{
  "entries": [
    {"entry_type": "character", "title": "...", "content": "..."},
    {"entry_type": "theme",     "title": "...", "content": "..."}
  ]
}
"""


# ---------------------------------------------------------------------------
# Bootstrap class
# ---------------------------------------------------------------------------

class BookBrainBootstrap:
    """
    Queries external sources in parallel and seeds the wiki before ingestion.

    Designed to fire as a parallel call alongside PDF extraction — not on the
    critical path. Failure is always silent; the main ingest loop is self-sufficient.
    """

    def __init__(
        self,
        store: BookBrainWikiStore,
        tavily_api_key: str,
        text_provider: ModelProvider = ModelProvider.CF,
        text_preset: str = "chat-knowledge",
        emb_provider: ModelProvider = ModelProvider.CF,
        emb_preset: str = "embedding-768",
    ):
        self.store = store
        self._tavily_api_key = tavily_api_key
        self._text_provider = text_provider
        self._text_preset = text_preset
        self._emb_provider = emb_provider
        self._emb_preset = emb_preset

    async def bootstrap(
        self,
        book_id: str,
        book_title: str,
        author: Optional[str] = None,
    ) -> BootstrapReport:
        """
        Run the full bootstrap pass for one book.
        Returns a BootstrapReport regardless of outcome — never raises.
        """
        t0 = time.monotonic()
        sources_queried = ["tavily", "wikipedia", "openlibrary", "gutenberg"]

        # All 4 fetches run concurrently — exceptions are caught internally
        tavily_text, wiki_text, ol_text, gutenberg_text = await asyncio.gather(
            self._fetch_tavily(book_title, author),
            self._fetch_wikipedia(book_title, author),
            self._fetch_openlibrary(book_title, author),
            self._fetch_gutenberg(book_title, author),
        )

        gathered: dict[str, str] = {}
        sources_succeeded: list[str] = []
        for label, source_key, text in [
            ("Tavily",           "tavily",       tavily_text),
            ("Wikipedia",        "wikipedia",    wiki_text),
            ("Open Library",     "openlibrary",  ol_text),
            ("Project Gutenberg","gutenberg",    gutenberg_text),
        ]:
            if text:
                gathered[label] = text
                sources_succeeded.append(source_key)

        entries_seeded = 0
        if gathered:
            entries_seeded = await self._compile_and_upsert(book_id, book_title, author, gathered)

        duration = time.monotonic() - t0
        logger.info(
            "BookBrain bootstrap [book=%s title=%r]: sources=%s entries=%d duration=%.1fs",
            book_id, book_title, sources_succeeded, entries_seeded, duration,
        )
        return BootstrapReport(
            book_id=book_id,
            book_title=book_title,
            sources_queried=sources_queried,
            sources_succeeded=sources_succeeded,
            entries_seeded=entries_seeded,
            duration_seconds=round(duration, 2),
        )

    # ------------------------------------------------------------------
    # Source fetchers — each returns None on any failure
    # ------------------------------------------------------------------

    async def _fetch_tavily(self, book_title: str, author: Optional[str]) -> Optional[str]:
        """4 concurrent Tavily web searches → concatenated result snippets."""
        author_str = author or ""
        queries = [
            q.format(title=book_title, author=author_str).strip()
            for q in _TAVILY_QUERIES
        ]

        async def _one(query: str) -> str:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.post(_TAVILY_URL, json={
                        "api_key": self._tavily_api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": 5,
                        "include_answer": True,
                    })
                    r.raise_for_status()
                    data = r.json()
                    parts = []
                    if data.get("answer"):
                        parts.append(data["answer"])
                    for result in data.get("results", []):
                        snippet = (result.get("content") or "")[:500]
                        if snippet:
                            parts.append(snippet)
                    return "\n".join(parts)
            except Exception as e:
                logger.debug("Tavily query failed [%r]: %s", query, e)
                return ""

        results = await asyncio.gather(*[_one(q) for q in queries])
        combined = "\n\n".join(r for r in results if r).strip()
        return combined or None

    async def _fetch_wikipedia(self, book_title: str, author: Optional[str]) -> Optional[str]:
        """Wikipedia REST API summary for the book's article."""
        encoded = quote(book_title.replace(" ", "_"), safe="")
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Audiobooker/1.0 (contact@audiobooker.io)"},
            ) as client:
                url = _WIKIPEDIA_SUMMARY_URL.format(title=encoded)
                r = await client.get(url)
                if r.status_code == 404:
                    # Try the "(novel)" disambiguation variant
                    url2 = _WIKIPEDIA_SUMMARY_URL.format(title=encoded + "_(novel)")
                    r = await client.get(url2)
                if r.status_code != 200:
                    return None
                data = r.json()
                extract = (data.get("extract") or "").strip()
                return extract or None
        except Exception as e:
            logger.debug("Wikipedia fetch failed [%r]: %s", book_title, e)
            return None

    async def _fetch_openlibrary(self, book_title: str, author: Optional[str]) -> Optional[str]:
        """Open Library search → work description, subjects, publish year."""
        params: dict = {
            "title": book_title,
            "limit": 1,
            "fields": "key,title,author_name,subject,first_publish_year",
        }
        if author:
            params["author"] = author
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                r = await client.get(_OPENLIBRARY_SEARCH_URL, params=params)
                r.raise_for_status()
                docs = r.json().get("docs", [])
                if not docs:
                    return None
                doc = docs[0]

                parts: list[str] = []
                if doc.get("title"):
                    parts.append(f"Title: {doc['title']}")
                if doc.get("author_name"):
                    parts.append(f"Author: {', '.join(doc['author_name'])}")
                if doc.get("first_publish_year"):
                    parts.append(f"First published: {doc['first_publish_year']}")
                if doc.get("subject"):
                    parts.append(f"Subjects/genres: {', '.join(doc['subject'][:20])}")

                # Fetch work description if available
                work_key = doc.get("key")
                if work_key:
                    r2 = await client.get(f"https://openlibrary.org{work_key}.json", timeout=8.0)
                    if r2.status_code == 200:
                        work = r2.json()
                        desc = work.get("description")
                        if isinstance(desc, dict):
                            desc = desc.get("value", "")
                        if desc:
                            parts.append(f"Description: {str(desc)[:1000]}")

                return "\n".join(parts) or None
        except Exception as e:
            logger.debug("OpenLibrary fetch failed [%r]: %s", book_title, e)
            return None

    async def _fetch_gutenberg(self, book_title: str, author: Optional[str]) -> Optional[str]:
        """
        Project Gutenberg via gutendex.com.
        For public domain books: returns opening 3000 chars of text.
        For anything else: returns structured metadata only.
        """
        query = f"{book_title} {author}".strip() if author else book_title
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.get(_GUTENDEX_URL, params={"search": query})
                r.raise_for_status()
                results = r.json().get("results", [])
                if not results:
                    return None

                book = results[0]
                authors = ", ".join(a.get("name", "") for a in book.get("authors", []))
                subjects = ", ".join(book.get("subjects", [])[:10])
                header = (
                    f"Project Gutenberg — {book.get('title', book_title)} by {authors}\n"
                    f"Subjects: {subjects}"
                )

                formats = book.get("formats", {})
                text_url = (
                    formats.get("text/plain; charset=utf-8")
                    or formats.get("text/plain")
                )
                if not text_url:
                    return header

                r2 = await client.get(text_url, timeout=20.0)
                if r2.status_code != 200:
                    return header

                snippet = r2.text[:3000].strip()
                return f"{header}\n\nOpening text:\n{snippet}"
        except Exception as e:
            logger.debug("Gutenberg fetch failed [%r]: %s", book_title, e)
            return None

    # ------------------------------------------------------------------
    # LLM compilation + upsert
    # ------------------------------------------------------------------

    async def _compile_and_upsert(
        self,
        book_id: str,
        book_title: str,
        author: Optional[str],
        gathered: dict[str, str],
    ) -> int:
        """
        Call the LLM to compile all gathered source text into structured wiki entries,
        then embed and upsert each one.
        Returns the count of entries successfully upserted.
        """
        author_line = f"Author: {author}\n" if author else ""
        source_blocks = "\n\n".join(
            f"### Source: {name}\n{text}" for name, text in gathered.items()
        )
        user_message = (
            f"Book: **{book_title}**\n"
            f"{author_line}"
            f"\nExtract structured wiki entries from the following sources:\n\n"
            f"{source_blocks}"
        )

        try:
            raw = await AITextService.chat_json(
                prompt_messages=[
                    ["system", _COMPILE_SYSTEM],
                    ["user", user_message],
                ],
                provider=self._text_provider,
                preset=self._text_preset,
            )
        except Exception as e:
            logger.warning("BookBrain bootstrap LLM compilation failed: %s", e)
            return 0

        items = raw.get("entries") or []
        if not items:
            logger.warning("BookBrain bootstrap: LLM returned no entries for %r", book_title)
            return 0

        count = 0
        for item in items:
            title = (item.get("title") or "").strip()
            content = (item.get("content") or "").strip()
            entry_type_raw = (item.get("entry_type") or "").strip().lower()
            if not title or not content:
                continue
            try:
                entry_type = EntryType(entry_type_raw)
            except ValueError:
                logger.debug("Bootstrap: skipping unknown entry_type %r", entry_type_raw)
                continue

            try:
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
                    source_chunk_indices=[_BOOTSTRAP_CHUNK_INDEX],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                await self.store.upsert_entry(entry)
                count += 1
            except Exception as e:
                logger.warning("Bootstrap: failed to upsert entry %r: %s", title, e)

        return count
