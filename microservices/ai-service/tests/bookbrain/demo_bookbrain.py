"""
BookBrain Demo — Chunking Use Case
====================================
Demonstrates BookBrain as a knowledge accumulator that improves
book chunking accuracy for the SpeakerChunker.

What this proves
----------------
SpeakerChunker has three brittle points:
  1. _discover_characters()  — hits web-RAG with the book title. Fails for
                               unknown/self-published books.
  2. alias_map construction  — LLM-guessed from prior knowledge. Misses
                               in-text aliases ("The Captain" = Marcus Vane).
  3. known_chars_str context — flat name list. No speech patterns, relationships,
                               or scene-level context for the attribution prompt.

BookBrain fixes all three by building the wiki organically from the text itself
as each chunk is processed, then making the accumulated knowledge retrievable
for subsequent chunks.

Usage
-----
  # From microservices/ai-service/
  python -m tests.bookbrain.demo_bookbrain

  # Against a non-default host:
  AI_SERVICE_URL=http://localhost:8000 python -m tests.bookbrain.demo_bookbrain

  # Skip the ingest phase and jump straight to search (wiki already populated):
  python -m tests.bookbrain.demo_bookbrain --search-only

  # Wipe the wiki and start fresh:
  python -m tests.bookbrain.demo_bookbrain --reset

Prerequisites
-------------
  - ai-service running (python main.py from ai-service/)
  - MongoDB accessible (same connection as ai-service)
  - API_V1_PREFIX set to /api/v1/ai_service in ai-service .env
"""

import argparse
import json
import os
import sys
import time
from typing import Optional

import httpx

from tests.bookbrain.mock_book_chunks import (
    BOOK_ID,
    BOOK_TITLE,
    DEMO_SEARCH_QUERIES,
    EXPECTED_CHARACTERS,
    build_mock_chunks,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL    = os.getenv("AI_SERVICE_URL", "http://127.0.0.1:8000")
API_PREFIX  = os.getenv("API_V1_PREFIX",  "/api/v1/ai_service")
BOOKBRAIN   = f"{BASE_URL}{API_PREFIX}/bookbrain"
TIMEOUT     = 120  # seconds — LLM calls can be slow

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

_SEP  = "─" * 70
_SEP2 = "═" * 70

def _h1(text: str) -> None:
    print(f"\n{_SEP2}")
    print(f"  {text}")
    print(_SEP2)

def _h2(text: str) -> None:
    print(f"\n{_SEP}")
    print(f"  {text}")
    print(_SEP)

def _ok(text: str) -> None:
    print(f"  [OK]  {text}")

def _info(text: str) -> None:
    print(f"  [..] {text}")

def _warn(text: str) -> None:
    print(f"  [!!] {text}")

def _json(data: dict, indent: int = 4) -> None:
    print(json.dumps(data, indent=indent, default=str))


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _post(client: httpx.Client, path: str, body: dict) -> dict:
    url = f"{BOOKBRAIN}/{path}"
    resp = client.post(url, json=body, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _get(client: httpx.Client, path: str, params: Optional[dict] = None) -> dict | list:
    url = f"{BOOKBRAIN}/{path}"
    resp = client.get(url, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _delete(client: httpx.Client, path: str) -> None:
    url = f"{BOOKBRAIN}/{path}"
    resp = client.delete(url, timeout=TIMEOUT)
    resp.raise_for_status()


# ---------------------------------------------------------------------------
# Phase 0 — health check
# ---------------------------------------------------------------------------

def check_health(client: httpx.Client) -> bool:
    _h1("PHASE 0 — Health Check")
    try:
        resp = client.get(f"{BASE_URL}{API_PREFIX}/health/", timeout=10)
        resp.raise_for_status()
        _ok(f"ai-service is up: {resp.json()}")
        return True
    except Exception as e:
        _warn(f"ai-service not reachable: {e}")
        _warn(f"Start it with: cd microservices/ai-service && python main.py")
        return False


# ---------------------------------------------------------------------------
# Phase 1 — reset
# ---------------------------------------------------------------------------

def reset_wiki(client: httpx.Client) -> None:
    _h2("Resetting existing wiki for this book_id...")
    try:
        _delete(client, BOOK_ID)
        _ok(f"Wiki cleared for book_id={BOOK_ID}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            _info("No existing wiki to clear.")
        else:
            _warn(f"Reset failed: {e}")


# ---------------------------------------------------------------------------
# Phase 2 — ingest chunks
# ---------------------------------------------------------------------------

def ingest_all_chunks(client: httpx.Client) -> None:
    _h1("PHASE 1 — Ingest Book Chunks (Building the Wiki)")
    chunks = build_mock_chunks()

    print(f"\n  Book:    {BOOK_TITLE}")
    print(f"  Book ID: {BOOK_ID}")
    print(f"  Chunks:  {len(chunks)}")
    print(f"\n  Each chunk goes through the agent loop:")
    print("    1. Embed chunk text")
    print("    2. Retrieve relevant wiki entries (empty on first pass)")
    print("    3. LLM extracts characters/themes/settings/plot/terminology")
    print("    4. Embed + upsert new/updated entries into MongoDB")
    print()

    total_retrieved = 0
    total_upserted  = 0

    total = len(chunks)
    for chunk in chunks:
        idx   = chunk["chunk_id"] - 1
        chars = chunk["character_count"]

        _info(f"Ingesting chunk {idx + 1}/{total} ({chars} chars)...")
        t0 = time.time()

        result = _post(client, f"{BOOK_ID}/ingest", {
            "chunk_text":   chunk["text"],
            "chunk_index":  idx,
            "book_title":   BOOK_TITLE,
            "total_chunks": total,
        })

        elapsed = time.time() - t0
        retrieved = result["retrieved_entries"]
        upserted  = result["upserted_entries"]
        total_retrieved += retrieved
        total_upserted  += upserted

        _ok(
            f"Chunk {idx}: retrieved={retrieved} wiki entries as context | "
            f"upserted={upserted} entries | {elapsed:.1f}s"
        )

        # Show what was upserted (first 2 IDs for brevity)
        if result["wiki_entry_ids"]:
            preview = result["wiki_entry_ids"][:2]
            suffix  = f" (+{len(result['wiki_entry_ids'])-2} more)" if len(result["wiki_entry_ids"]) > 2 else ""
            print(f"       entry_ids: {preview}{suffix}")

    print(f"\n  TOTALS: retrieved={total_retrieved} | upserted={total_upserted}")


# ---------------------------------------------------------------------------
# Phase 2a — narrative cursor
# ---------------------------------------------------------------------------

def inspect_narrative_cursor(client: httpx.Client) -> None:
    _h1("PHASE 2a — Narrative Cursor (The 'Story So Far' Index File)")
    print()
    print("  Karpathy: 'the LLM has been pretty good about auto-maintaining")
    print("  index files and brief summaries of all the documents'")
    print()
    print("  This entry is updated on EVERY chunk. It gives the LLM ordered")
    print("  narrative context regardless of what semantic search returns.")
    print("  Without it, chunk 15 has no idea what happened in chunks 0-14.\n")

    entries = _get(client, f"{BOOK_ID}/wiki", params={"entry_type": "summary"})
    cursor  = next((e for e in entries if e["title"].lower() == "story so far"), None)

    if not cursor:
        _warn("No 'Story So Far' entry found — LLM may have skipped the mandatory cursor.")
        return

    chunks_covered = sorted(cursor["source_chunk_indices"])
    _ok(f"Cursor exists. Covers chunks: {chunks_covered}")
    print()
    print("  CONTENT:")
    print()
    for line in cursor["content"].splitlines():
        print(f"  {line}")
    print()


# ---------------------------------------------------------------------------
# Phase 3 — inspect the full wiki
# ---------------------------------------------------------------------------

def inspect_wiki(client: httpx.Client) -> None:
    _h1("PHASE 2 — Wiki Contents (What the Chunker Would Now Know)")

    all_entries = _get(client, f"{BOOK_ID}/wiki")
    if not all_entries:
        _warn("Wiki is empty — did ingest run successfully?")
        return

    # Group by entry type
    by_type: dict[str, list] = {}
    for e in all_entries:
        by_type.setdefault(e["entry_type"], []).append(e)

    total = len(all_entries)
    print(f"\n  Total entries: {total}")
    print(f"  By type: { {k: len(v) for k, v in by_type.items()} }\n")

    # ---- Characters — the most important for chunking ----
    if "character" in by_type:
        _h2("CHARACTER entries (replaces _discover_characters() web-RAG)")
        print()
        print("  These replace the SpeakerChunker web-RAG call for books the LLM")
        print("  doesn't know. Built from raw text — no prior knowledge needed.\n")
        for e in by_type["character"]:
            print(f"  [{e['title']}]")
            print(f"  {e['content'][:300].strip()}")
            print(f"  Sources: chunks {e['source_chunk_indices']}")
            print()

    # ---- Settings ----
    if "setting" in by_type:
        _h2("SETTING entries")
        for e in by_type["setting"]:
            print(f"  [{e['title']}]  {e['content'][:200].strip()}\n")

    # ---- Plot ----
    if "plot" in by_type:
        _h2("PLOT entries")
        for e in by_type["plot"]:
            print(f"  [{e['title']}]  {e['content'][:200].strip()}\n")

    # ---- Themes ----
    if "theme" in by_type:
        _h2("THEME entries")
        for e in by_type["theme"]:
            print(f"  [{e['title']}]  {e['content'][:200].strip()}\n")


# ---------------------------------------------------------------------------
# Phase 4 — semantic search demo
# ---------------------------------------------------------------------------

def run_search_demo(client: httpx.Client) -> None:
    _h1("PHASE 3 — Semantic Search (Chunker Context Retrieval)")
    print()
    print("  These queries show what the SpeakerChunker's scene attribution prompt")
    print("  could retrieve before asking the LLM 'who said this?'\n")

    for query_text, expected_type in DEMO_SEARCH_QUERIES:
        _h2(f"Query: \"{query_text}\"")
        result = _post(client, f"{BOOK_ID}/wiki/search", {
            "query":   query_text,
            "top_k":   3,
        })

        results = result.get("results", [])
        scores  = result.get("scores",  [])

        if not results:
            _warn("No results returned.")
            continue

        for entry, score in zip(results, scores):
            type_label = entry["entry_type"].upper()
            title      = entry["title"]
            content    = entry["content"][:200].strip()
            chunks     = entry["source_chunk_indices"]
            print(f"  [{type_label}] {title}  (score={score:.3f}, chunks={chunks})")
            print(f"  {content}")
            print()


# ---------------------------------------------------------------------------
# Phase 5 — alias map extraction
# ---------------------------------------------------------------------------

def extract_alias_map(client: httpx.Client) -> None:
    _h1("PHASE 4 — Alias Map Extraction (Replaces LLM Guesswork)")
    print()
    print("  SpeakerChunker builds alias_map by asking the LLM what nicknames")
    print("  a character has — risky for unknown books. BookBrain finds aliases")
    print("  in-text. Here is what was captured:\n")

    char_entries = _get(client, f"{BOOK_ID}/wiki", params={"entry_type": "character"})
    if not char_entries:
        _warn("No character entries found.")
        return

    print("  Detected characters (from wiki content — check for alias mentions):\n")
    for e in char_entries:
        print(f"  Title : {e['title']}")
        content = e["content"]
        # Surface alias clues — look for alias-like patterns in content
        alias_hints = [
            line.strip() for line in content.split(".")
            if any(w in line.lower() for w in ("called", "alias", "nickname", "known as", "short for", "the captain", "roz"))
        ]
        if alias_hints:
            print(f"  Alias clues from wiki:")
            for hint in alias_hints[:3]:
                print(f"    • {hint}")
        print()

    print("  Expected alias map (ground truth from mock data):\n")
    for c in EXPECTED_CHARACTERS:
        aliases = " | ".join(c["aliases"])
        print(f"  {c['name']:<25} → [{aliases}]  — {c['role']}")


# ---------------------------------------------------------------------------
# Phase 6 — markdown export
# ---------------------------------------------------------------------------

def export_wiki(client: httpx.Client) -> None:
    _h1("PHASE 5 — Wiki Export (Upload to R2 for Cross-Service Use)")
    print()
    print("  The exported Markdown can be uploaded to R2 at:")
    print(f"  bookbrain/{BOOK_ID}/wiki.md\n")

    result = _get(client, f"{BOOK_ID}/export")
    md = result.get("markdown", "")

    # Print first 60 lines
    lines = md.splitlines()
    preview_lines = lines[:60]
    print("\n".join(f"  {l}" for l in preview_lines))
    if len(lines) > 60:
        print(f"\n  ... ({len(lines) - 60} more lines)")

    print(f"\n  Total: {len(md)} chars across {len(lines)} lines")


# ---------------------------------------------------------------------------
# Phase 7 — chunker integration summary
# ---------------------------------------------------------------------------

def print_chunker_integration_summary() -> None:
    _h1("PHASE 6 — How This Plugs Into SpeakerChunker")
    print("""
  BEFORE BookBrain (current code):
  ─────────────────────────────────
  _discover_characters(book_title, full_text)
    → sync_rag_chat() hits web search with book title
    → Works only for books the LLM knows
    → Has a breakpoint() in it right now (won't run at all)
    → Returns flat list of {name, aliases, gender, description}

  WITH BookBrain (proposed integration):
  ───────────────────────────────────────
  Step 0 (before chunk_by_speaker):
    Feed each raw chunk through:
      POST /bookbrain/{book_id}/ingest
    This runs BEFORE speaker attribution, using TextChunker output directly.

  Step 3 replacement (_discover_characters):
    GET /bookbrain/{book_id}/wiki?entry_type=character
    → Returns characters built from actual text, not web knowledge
    → Includes alias clues found in-text ("The Captain", "Roz")
    → Works for ANY book including unpublished ones

  Step 5 scene system prompt enrichment:
    POST /bookbrain/{book_id}/wiki/search
      body: {"query": "<scene text excerpt>", "top_k": 5}
    → Returns relevant characters, settings, plot context
    → Inject into known_chars_str and system prompt for richer attribution

  Step 6 alias map construction:
    Character wiki entries contain alias clues from in-text evidence
    → More accurate than LLM knowledge for alias resolution

  INTEGRATION POINT in llm_speaker_chunker.py:
  ──────────────────────────────────────────────
  Replace this block (Step 3):
    characters = self._discover_characters(book_title, full_text)

  With:
    characters = await self._discover_characters_from_bookbrain(book_id)
    # falls back to existing web-RAG if wiki is empty

  (This is the v1 we'll implement once the team pushes their updates.)
    """)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="BookBrain demo — chunking use case")
    parser.add_argument("--reset",       action="store_true", help="Delete the wiki for this book_id before running")
    parser.add_argument("--search-only", action="store_true", help="Skip ingest, only run search and export phases")
    parser.add_argument("--ingest-only", action="store_true", help="Only run ingest phase")
    args = parser.parse_args()

    print()
    print("  BookBrain Demo — Book Chunking Use Case")
    print(f"  Book:    {BOOK_TITLE}")
    print(f"  Book ID: {BOOK_ID}")
    print(f"  Service: {BOOKBRAIN}")

    with httpx.Client() as client:
        if not check_health(client):
            sys.exit(1)

        if args.reset:
            reset_wiki(client)

        if not args.search_only:
            ingest_all_chunks(client)

        if args.ingest_only:
            print("\n  Ingest complete. Run without --ingest-only to see the wiki.")
            return

        inspect_narrative_cursor(client)
        inspect_wiki(client)
        run_search_demo(client)
        extract_alias_map(client)
        export_wiki(client)
        print_chunker_integration_summary()

    _h1("DEMO COMPLETE")
    print(f"\n  Wiki persists in MongoDB — book_id: {BOOK_ID}")
    print(f"  Run with --reset to start fresh.\n")


if __name__ == "__main__":
    main()
