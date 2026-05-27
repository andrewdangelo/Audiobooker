"""
BookBrain — Project Gutenberg Integration Test
==============================================
Tests the full BookBrain pipeline against real public domain text.

Book: The Adventures of Sherlock Holmes (Gutenberg #1661)
      Arthur Conan Doyle — "A Scandal in Bohemia" (first story)

Why Sherlock Holmes:
  - Instantly recognisable characters and setting (easy to verify LLM output)
  - First-person narrator (Watson) with a named secondary POV (Holmes)
  - Alias challenge: "the woman" = Irene Adler; Watson uses "Holmes" not full name
  - Clear themes: deduction, observation, disguise
  - 221B Baker Street — concrete, well-known setting to test retrieval

Run as an integration test (requires live ai-service on port 8000):
    pytest tests/bookbrain/test_gutenberg_integration.py -v -s -m integration

Run as a standalone demo script:
    python -m tests.bookbrain.test_gutenberg_integration
    python -m tests.bookbrain.test_gutenberg_integration --reset
    python -m tests.bookbrain.test_gutenberg_integration --chunks 5 --skip-bootstrap

The downloaded text is cached locally at:
    tests/bookbrain/gutenberg_cache/sherlock_holmes_1661.txt
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import pytest

# ---------------------------------------------------------------------------
# Book config
# ---------------------------------------------------------------------------

GUTENBERG_ID    = 1661
GUTENBERG_TITLE = "The Adventures of Sherlock Holmes"
GUTENBERG_AUTHOR = "Arthur Conan Doyle"
GUTENBERG_TEXT_URL = "https://www.gutenberg.org/files/1661/1661-0.txt"

BOOK_ID         = "gutenberg-sherlock-1661"
BASE_URL        = "http://localhost:8000/api/v1"

CHUNK_SIZE      = 1_500   # chars per chunk — realistic chunker output
CHUNK_OVERLAP   = 150     # chars of overlap between chunks
DEFAULT_CHUNKS  = 8       # covers most of "A Scandal in Bohemia" opening

CACHE_DIR  = Path(__file__).parent / "gutenberg_cache"
CACHE_FILE = CACHE_DIR / "sherlock_holmes_1661.txt"

# ---------------------------------------------------------------------------
# Expected outputs — what a correct BookBrain run should find
# ---------------------------------------------------------------------------

EXPECTED_CHARACTERS = [
    {
        "name": "Sherlock Holmes",
        "aliases": ["Holmes"],
        "role": "Consulting detective",
        "markers": ["detective", "observe", "deduc"],
    },
    {
        "name": "Dr. Watson",
        "aliases": ["Watson", "John Watson"],
        "role": "Narrator and companion",
        "markers": ["narrat", "doctor", "compan", "watson"],
    },
    {
        "name": "Irene Adler",
        "aliases": ["the woman"],
        "role": "Opera singer, central figure of the case",
        "markers": ["adler", "woman", "opera", "singer"],
    },
    {
        "name": "King of Bohemia",
        "aliases": ["the King", "Count Von Kramm", "Wilhelm"],
        "role": "Client — seeks to recover a compromising photograph",
        "markers": ["king", "bohemia", "photograph", "client"],
    },
]

EXPECTED_SETTINGS = [
    "221B Baker Street",
    "London",
]

EXPECTED_THEMES = [
    "observation",
    "deduction",
    "disguise",
]

SEARCH_QUERIES = [
    ("Who is Sherlock Holmes and what is his profession?",  "character"),
    ("Where do Holmes and Watson live?",                    "setting"),
    ("What is the significance of the photograph?",         "plot"),
    ("How does Holmes deduce information from observation?","theme"),
    ("Who is Irene Adler?",                                 "character"),
]

# ---------------------------------------------------------------------------
# Gutenberg text fetcher + chunker
# ---------------------------------------------------------------------------

async def fetch_gutenberg_text() -> str:
    """
    Download the Gutenberg text and cache it locally.
    Returns the story text stripped of Gutenberg legal headers/footers.
    """
    CACHE_DIR.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        raw = CACHE_FILE.read_text(encoding="utf-8", errors="replace")
        print(f"  [cache] Loaded from {CACHE_FILE.name} ({len(raw):,} chars)")
    else:
        print(f"  [download] Fetching Gutenberg #{GUTENBERG_ID}...")
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "Audiobooker/1.0 (test)"},
        ) as client:
            r = await client.get(GUTENBERG_TEXT_URL)
            r.raise_for_status()
        raw = r.text
        CACHE_FILE.write_text(raw, encoding="utf-8")
        print(f"  [download] Saved {len(raw):,} chars to {CACHE_FILE.name}")

    return _strip_gutenberg_boilerplate(raw)


def _strip_gutenberg_boilerplate(raw: str) -> str:
    """Strip Gutenberg legal header/footer, returning only story text."""
    start_marker = re.compile(
        r"\*\*\* ?START OF THE PROJECT GUTENBERG EBOOK .+? \*\*\*", re.IGNORECASE
    )
    end_marker = re.compile(
        r"\*\*\* ?END OF THE PROJECT GUTENBERG EBOOK .+? \*\*\*", re.IGNORECASE
    )

    m_start = start_marker.search(raw)
    if m_start:
        raw = raw[m_start.end():]

    m_end = end_marker.search(raw)
    if m_end:
        raw = raw[: m_end.start()]

    return raw.strip()


def make_chunks(text: str, n: int, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Split text into n chunks of `size` chars with `overlap` chars of context carry-over.
    Breaks are moved to the nearest whitespace boundary so words are never cut mid-stream.
    Returns list of dicts in the same shape as TextChunker output.
    """
    chunks = []
    start = 0
    offset = 0

    while len(chunks) < n and start < len(text):
        end = min(start + size, len(text))

        # Extend to nearest whitespace so we don't cut a word
        if end < len(text):
            ws = text.rfind(" ", start, end + 50)
            if ws > start:
                end = ws

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append({
                "chunk_id":        len(chunks),
                "text":            chunk_text,
                "page_numbers":    [len(chunks) + 1],
                "character_count": len(chunk_text),
                "start_char":      offset,
                "end_char":        offset + len(chunk_text),
            })
            offset += len(chunk_text)

        start = end - overlap  # carry-over for context continuity

    return chunks


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

async def reset_wiki(client: httpx.AsyncClient):
    try:
        await client.delete(f"{BASE_URL}/bookbrain/{BOOK_ID}", timeout=10.0)
    except Exception:
        pass


async def run_bootstrap(client: httpx.AsyncClient) -> dict:
    r = await client.post(
        f"{BASE_URL}/bookbrain/{BOOK_ID}/bootstrap",
        json={"book_title": GUTENBERG_TITLE, "author": GUTENBERG_AUTHOR},
        timeout=90.0,
    )
    r.raise_for_status()
    return r.json()


async def ingest_chunk(client: httpx.AsyncClient, chunk: dict, total: int) -> dict:
    r = await client.post(
        f"{BASE_URL}/bookbrain/{BOOK_ID}/ingest",
        json={
            "chunk_text":   chunk["text"],
            "chunk_index":  chunk["chunk_id"],
            "book_title":   GUTENBERG_TITLE,
            "total_chunks": total,
        },
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


async def get_wiki(client: httpx.AsyncClient, entry_type: Optional[str] = None) -> list:
    params = {}
    if entry_type:
        params["entry_type"] = entry_type
    r = await client.get(f"{BASE_URL}/bookbrain/{BOOK_ID}/wiki", params=params, timeout=15.0)
    r.raise_for_status()
    return r.json()


async def search_wiki(client: httpx.AsyncClient, query: str, top_k: int = 3) -> dict:
    r = await client.post(
        f"{BASE_URL}/bookbrain/{BOOK_ID}/wiki/search",
        json={"query": query, "top_k": top_k},
        timeout=20.0,
    )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# Validation helpers — shared by pytest and script modes
# ---------------------------------------------------------------------------

def check_narrative_cursor(entries: list) -> dict:
    summaries = [e for e in entries if e["entry_type"] == "summary"]
    cursor    = next((e for e in summaries if "story so far" in e["title"].lower()), None)
    return {
        "found":   cursor is not None,
        "content": cursor["content"][:200] if cursor else "",
    }


def check_characters(entries: list) -> list[dict]:
    all_titles   = " ".join(e["title"].lower() for e in entries)
    all_content  = " ".join(e["content"].lower() for e in entries)
    all_text     = all_titles + " " + all_content
    results = []
    for ec in EXPECTED_CHARACTERS:
        name_hit  = ec["name"].lower() in all_text
        alias_hit = any(a.lower() in all_text for a in ec["aliases"])
        marker_hit = any(m in all_content for m in ec["markers"])
        found = name_hit or alias_hit or marker_hit
        results.append({
            "name":       ec["name"],
            "found":      found,
            "name_hit":   name_hit,
            "alias_hit":  alias_hit,
            "marker_hit": marker_hit,
        })
    return results


def check_settings(entries: list) -> list[dict]:
    all_content = " ".join(
        (e["title"] + " " + e["content"]).lower()
        for e in entries
    )
    return [
        {"name": s, "found": s.lower() in all_content}
        for s in EXPECTED_SETTINGS
    ]


def check_search_results(results: list[dict], expected_type: str) -> dict:
    if not results:
        return {"top_type": "none", "match": False}
    top = results[0]
    return {
        "top_type":    top["entry_type"],
        "top_title":   top["title"],
        "match":       top["entry_type"] == expected_type,
    }


# ---------------------------------------------------------------------------
# pytest integration tests
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def event_loop():
    """Module-scoped event loop so all tests share one async context."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def gutenberg_text():
    """Download (or load from cache) the Sherlock Holmes text once per session."""
    return await fetch_gutenberg_text()


@pytest.fixture(scope="module")
async def populated_wiki(gutenberg_text):
    """
    Run the full pipeline once per module — bootstrap + 8 chunk ingest.
    All assertion tests below share this populated wiki.
    """
    chunks = make_chunks(gutenberg_text, DEFAULT_CHUNKS)
    async with httpx.AsyncClient() as client:
        await reset_wiki(client)
        # Bootstrap
        bootstrap_result = await run_bootstrap(client)
        # Ingest
        for chunk in chunks:
            await ingest_chunk(client, chunk, len(chunks))
        # Fetch wiki for assertions
        entries = await get_wiki(client)
    return {
        "entries":   entries,
        "bootstrap": bootstrap_result,
        "chunks":    chunks,
    }


@pytest.mark.asyncio
async def test_bootstrap_seeds_entries(populated_wiki):
    """Bootstrap should seed at least 1 entry from external sources."""
    bs = populated_wiki["bootstrap"]
    assert len(bs["sources_succeeded"]) > 0, "No sources succeeded"
    assert bs["entries_seeded"] > 0, (
        f"Bootstrap seeded 0 entries (sources: {bs['sources_succeeded']})"
    )


@pytest.mark.asyncio
async def test_wiki_has_minimum_entries(populated_wiki):
    """After 8 chunks the wiki should have at least 10 entries."""
    entries = populated_wiki["entries"]
    assert len(entries) >= 10, (
        f"Expected ≥10 wiki entries, got {len(entries)}"
    )


@pytest.mark.asyncio
async def test_narrative_cursor_exists(populated_wiki):
    """The 'Story So Far' entry must always be produced by the agent."""
    result = check_narrative_cursor(populated_wiki["entries"])
    assert result["found"], (
        "Narrative cursor ('Story So Far') not found in wiki — "
        "agent may have dropped the mandatory summary entry"
    )


@pytest.mark.asyncio
async def test_sherlock_holmes_in_wiki(populated_wiki):
    """Sherlock Holmes must appear as a character entry."""
    char_results = check_characters(populated_wiki["entries"])
    holmes = next(r for r in char_results if "Holmes" in r["name"])
    assert holmes["found"], (
        "Sherlock Holmes not found in wiki entries — character extraction failed"
    )


@pytest.mark.asyncio
async def test_watson_in_wiki(populated_wiki):
    """Dr. Watson (narrator) must appear as a character entry."""
    char_results = check_characters(populated_wiki["entries"])
    watson = next(r for r in char_results if "Watson" in r["name"])
    assert watson["found"], (
        "Dr. Watson not found in wiki entries — "
        "first-person narrator should always be extracted"
    )


@pytest.mark.asyncio
async def test_irene_adler_in_wiki(populated_wiki):
    """Irene Adler must appear — she is the central figure of the story."""
    char_results = check_characters(populated_wiki["entries"])
    adler = next(r for r in char_results if "Adler" in r["name"])
    assert adler["found"], (
        "Irene Adler not found in wiki entries — "
        "central character of 'A Scandal in Bohemia' should be extracted"
    )


@pytest.mark.asyncio
async def test_baker_street_setting(populated_wiki):
    """221B Baker Street should be captured as a setting entry."""
    setting_results = check_settings(populated_wiki["entries"])
    baker_st = next(r for r in setting_results if "Baker Street" in r["name"])
    assert baker_st["found"], (
        "221B Baker Street not found in wiki — "
        "setting extraction from 'Holmes's chambers' description failed"
    )


@pytest.mark.asyncio
async def test_semantic_search_finds_holmes():
    """Searching for Holmes should surface a character entry as the top result."""
    async with httpx.AsyncClient() as client:
        result = await search_wiki(client, "Sherlock Holmes consulting detective methods")
    results = result.get("results", [])
    assert results, "Search returned no results"
    top_type = results[0]["entry_type"]
    assert top_type == "character", (
        f"Expected top search result for 'Sherlock Holmes' to be 'character', got '{top_type}'"
    )


@pytest.mark.asyncio
async def test_semantic_search_finds_setting():
    """Searching for Baker Street should surface the setting entry."""
    async with httpx.AsyncClient() as client:
        result = await search_wiki(client, "Where does Holmes live Baker Street")
    results = result.get("results", [])
    assert results, "Search returned no results"
    top_type = results[0]["entry_type"]
    assert top_type in ("setting", "character"), (
        f"Expected 'setting' or 'character', got '{top_type}'"
    )


@pytest.mark.asyncio
async def test_entry_types_are_diverse(populated_wiki):
    """A properly enriched wiki should have at least 3 distinct entry types."""
    types = {e["entry_type"] for e in populated_wiki["entries"]}
    assert len(types) >= 3, (
        f"Expected ≥3 entry types, got {types} — "
        "LLM may be producing only one type of entry"
    )


# ---------------------------------------------------------------------------
# Standalone demo script
# ---------------------------------------------------------------------------

W = 62

def _hr(): return "─" * W
def _section(title): print(f"\n  {title}\n  {_hr()}")
def _row(label, value, w=34):
    print(f"  {label} {'.' * (w - len(label))} {value}")
def _ok(b): return "✅" if b else "❌"


async def run_demo(n_chunks: int, skip_bootstrap: bool, reset: bool):
    print()
    print("╔" + "═" * W + "╗")
    title = f"BOOKBRAIN — GUTENBERG INTEGRATION TEST"
    pad = (W - len(title) - 2) // 2
    print(f"║{' ' * pad}{title}{' ' * (W - pad - len(title))}║")
    sub = f"The Adventures of Sherlock Holmes — {n_chunks} chunks"
    pad2 = (W - len(sub) - 2) // 2
    print(f"║{' ' * pad2}{sub}{' ' * (W - pad2 - len(sub))}║")
    print("╚" + "═" * W + "╝")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Service: {BASE_URL}")

    t_total = time.monotonic()

    # --- Fetch text ---
    _section("Step 1 │ Fetch Gutenberg Text")
    story_text = await fetch_gutenberg_text()
    chunks = make_chunks(story_text, n_chunks)
    total_chars = sum(c["character_count"] for c in chunks)
    _row("Story chars (total)", f"{len(story_text):,}")
    _row("Chunks to ingest",    str(len(chunks)))
    _row("Chars to ingest",     f"{total_chars:,}")
    _row("Chunk size",          f"{CHUNK_SIZE} chars  (overlap={CHUNK_OVERLAP})")

    async with httpx.AsyncClient() as client:

        # --- Health check ---
        try:
            r = await client.get(BASE_URL.replace("/api/v1", "/"), timeout=5.0)
            health_ok = r.status_code < 300
        except Exception:
            health_ok = False
        if not health_ok:
            print("\n  ❌ ai-service not reachable at", BASE_URL)
            print("     Start it with: python main.py")
            return

        # --- Reset ---
        if reset:
            _section("Reset")
            await reset_wiki(client)
            print("  Wiki cleared.")

        # --- Bootstrap ---
        bootstrap_result = None
        if not skip_bootstrap:
            _section("Step 2 │ Bootstrap (external sources)")
            t0 = time.monotonic()
            try:
                bootstrap_result = await run_bootstrap(client)
                bs_dur = time.monotonic() - t0
                ok   = bootstrap_result["entries_seeded"] > 0
                succ = bootstrap_result["sources_succeeded"]
                _row("Sources succeeded", f"{len(succ)}/4  ({', '.join(succ)})")
                _row("Entries seeded",    str(bootstrap_result["entries_seeded"]))
                _row("Duration",          f"{bs_dur:.1f}s")
                _row("Verdict",           "✅ PASS" if ok else "⚠️  0 entries (graceful)")
            except Exception as e:
                print(f"  ⚠️  Bootstrap failed (non-fatal): {e}")

        # --- Ingest ---
        _section(f"Step 3 │ Chunk Ingestion ({len(chunks)} chunks)")
        ingest_timings = []
        t_ingest = time.monotonic()
        for chunk in chunks:
            t0 = time.monotonic()
            try:
                resp = await ingest_chunk(client, chunk, len(chunks))
                dur  = time.monotonic() - t0
                ingest_timings.append({"dur": dur, "ok": True, "chars": chunk["character_count"]})
                upserted = resp.get("upserted_entries", "?")
                print(f"    Chunk {chunk['chunk_id']:>2} ({chunk['character_count']:>5,} chars) "
                      f"... {dur:.1f}s  ✅  +{upserted} entries")
            except Exception as e:
                dur = time.monotonic() - t0
                ingest_timings.append({"dur": dur, "ok": False, "chars": chunk["character_count"]})
                print(f"    Chunk {chunk['chunk_id']:>2} ... ❌ {e}")

        ingest_total = time.monotonic() - t_ingest
        ingest_chars = sum(t["chars"] for t in ingest_timings)
        throughput   = ingest_chars / ingest_total if ingest_total else 0
        avg_chunk    = ingest_total / len(ingest_timings) if ingest_timings else 0
        _row("Total duration",  f"{ingest_total:.1f}s")
        _row("Throughput",      f"{throughput:.0f} chars/sec")
        _row("Avg per chunk",   f"{avg_chunk:.1f}s")

        # --- Wiki audit ---
        _section("Step 4 │ Wiki Quality Audit")
        entries = await get_wiki(client)
        by_type: dict[str, int] = {}
        for e in entries:
            by_type[e["entry_type"]] = by_type.get(e["entry_type"], 0) + 1
        _row("Total entries", str(len(entries)))
        for etype, count in sorted(by_type.items()):
            _row(f"  → {etype}", str(count))

        print()
        cursor_result = check_narrative_cursor(entries)
        _row("Narrative cursor", _ok(cursor_result["found"]) + "  'Story So Far'")
        if cursor_result["content"]:
            print(f"\n    Preview: \"{cursor_result['content'][:120]}...\"")

        print()
        char_results  = check_characters(entries)
        found_count   = sum(1 for c in char_results if c["found"])
        _row("Expected characters", f"{found_count}/{len(EXPECTED_CHARACTERS)}")
        for cr in char_results:
            method = []
            if cr["name_hit"]:   method.append("name")
            if cr["alias_hit"]:  method.append("alias")
            if cr["marker_hit"]: method.append("keyword")
            _row(f"  {_ok(cr['found'])} {cr['name']}",
                 f"via {'+'.join(method)}" if method else "not found")

        print()
        setting_results = check_settings(entries)
        for sr in setting_results:
            _row(f"  {_ok(sr['found'])} {sr['name']}", "")

        # --- Search ---
        _section("Step 5 │ Semantic Search Validation")
        type_hits = 0
        for query, expected_type in SEARCH_QUERIES:
            t0 = time.monotonic()
            try:
                resp  = await search_wiki(client, query)
                dur   = time.monotonic() - t0
                srch  = check_search_results(resp.get("results", []), expected_type)
                hit   = srch["match"]
                if hit:
                    type_hits += 1
                icon  = "✅" if hit else "⚠️ "
                print(f"    {dur:.3f}s  {icon}  top={srch['top_type']:<12}"
                      f"  \"{query[:38]}\"")
            except Exception as e:
                print(f"    ❌ ERROR: {e}")
        _row("Type match rate", f"{type_hits}/{len(SEARCH_QUERIES)}")

    total_dur = time.monotonic() - t_total

    # --- Summary ---
    all_chars_ingested = all(t["ok"] for t in ingest_timings)
    overall = (
        found_count >= 2
        and cursor_result["found"]
        and all_chars_ingested
        and len(entries) >= 8
    )

    print()
    print(f"  {'═' * W}")
    print(f"  GUTENBERG INTEGRATION SUMMARY")
    print(f"  {'═' * W}")
    _row("Book",               f"{GUTENBERG_TITLE}")
    _row("Author",             GUTENBERG_AUTHOR)
    _row("Chunks ingested",    f"{len(ingest_timings)} × ~{CHUNK_SIZE} chars")
    _row("Total chars",        f"{ingest_chars:,}")
    _row("Wiki entries built", str(len(entries)))
    _row("Characters found",   f"{found_count}/{len(EXPECTED_CHARACTERS)}")
    _row("Narrative cursor",   _ok(cursor_result["found"]))
    _row("Search type match",  f"{type_hits}/{len(SEARCH_QUERIES)}")
    _row("Throughput",         f"{throughput:.0f} chars/sec")
    _row("Total runtime",      f"{total_dur:.1f}s")
    print(f"  {'─' * W}")
    verdict = "✅  INTEGRATION TEST PASSED" if overall else "⚠️   PARTIAL — see results above"
    print(f"  VERDICT ............... {verdict}")
    print(f"  {'═' * W}")
    print()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="BookBrain Gutenberg Integration Test — The Adventures of Sherlock Holmes"
    )
    p.add_argument("--chunks",          type=int, default=DEFAULT_CHUNKS,
                   help=f"Number of chunks to ingest (default: {DEFAULT_CHUNKS})")
    p.add_argument("--skip-bootstrap",  action="store_true",
                   help="Skip the bootstrap phase")
    p.add_argument("--reset",           action="store_true",
                   help="Delete existing wiki for this book before running")
    p.add_argument("--base-url",        default=BASE_URL,
                   help=f"ai-service base URL (default: {BASE_URL})")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    BASE_URL = args.base_url
    asyncio.run(run_demo(
        n_chunks=args.chunks,
        skip_bootstrap=args.skip_bootstrap,
        reset=args.reset,
    ))
