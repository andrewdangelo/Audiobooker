# Claude Checkpoint — May 18, 2026
## Audiobooker — BookBrain Feature Session Summary

This file is a handoff checkpoint from a Claude Code session. Use it to pick up where we left off.
Tell Claude: "Read matt_claude_checkpoints_5_18_26.md and continue from where we left off."

---

## What BookBrain Is

BookBrain is a **Karpathy-style living wiki** for book text — an LLM that maintains a growing per-book knowledge base from raw source documents.

Karpathy's own framing:
> "Raw data is collected, then compiled by an LLM into a .md wiki, then operated on by various CLIs by the LLM to do Q&A and to incrementally enhance the wiki. You rarely ever write or edit the wiki manually — it's the domain of the LLM."

Applied to Audiobooker:
- **MongoDB** = wiki storage substrate
- **LLM** = the programmer that writes and maintains every entry
- **Chunk stream** = the raw/ directory being ingested in order
- **bookbrain/** = the compiled wiki that grows with every chunk

**Primary use case: book chunking accuracy.** Gives the SpeakerChunker a verified character list, alias maps, and speech pattern data before it starts attributing dialogue. Prevents hallucinated characters and alias confusion on long books.

**Secondary use case: reader product.** The wiki also functions as an interactive knowledge map — characters, themes, plot — surfaceable to readers as a book companion.

---

## Files Created / Modified

### ai-service — New Files

| File | Purpose |
|------|---------|
| `app/bookbrain/__init__.py` | Package init (empty) |
| `app/bookbrain/schemas.py` | All Pydantic models for BookBrain |
| `app/bookbrain/wiki_store.py` | MongoDB CRUD + cosine similarity search |
| `app/bookbrain/agent.py` | Per-chunk ingest agent (the core loop) |
| `app/bookbrain/linter.py` | Periodic enrichment pass (background job) |
| `app/bookbrain/bootstrap.py` | Pre-ingestion external source seeding |
| `app/routers/bookbrain.py` | REST API router for all BookBrain endpoints |

### ai-service — Modified Files

| File | Change |
|------|--------|
| `main.py` | Creates `bookbrain_wiki` collection + index, instantiates `BookBrainWikiStore` + `BookBrainAgent`, registers `/bookbrain` router |

### pdf-processor — Modified Files

| File | Change |
|------|--------|
| `app/core/config_settings.py` | Added `AI_SERVICE_BASE_URL` setting |
| `app/services/pipeline_client.py` | Added `trigger_bookbrain_bootstrap()` function |

### Test Files

| File | Purpose |
|------|---------|
| `tests/bookbrain/mock_book_chunks.py` | Fictional book "The Iron Letter" — 6 mock chunks in TextChunker shape |
| `tests/bookbrain/demo_bookbrain.py` | End-to-end demo script (6 phases, no real book needed) |
| `tests/bookbrain/test_linter.py` | 9 unit tests for BookBrainLinter (no DB, no LLM) |

---

## API Endpoints

All routes are under `{API_V1_PREFIX}/bookbrain` (ai-service, port 8000).

### POST `/{book_id}/bootstrap`
Seed the wiki from external public sources **before ingestion begins**.

Queries 4 sources concurrently (~15–25s total):
- **Tavily** — 4 parallel web searches: characters, themes, plot summary, literary analysis
- **Wikipedia** — REST summary API (free, no key beyond TAVILY_API_KEY)
- **Open Library** — work description, subjects, genres, publish year
- **Project Gutenberg** — opening 3000 chars of text for public domain books

All sources are gracefully degraded — any failure is silent, the ingest loop is self-sufficient without bootstrap data. Bootstrap entries are stored with `source_chunk_index=-1` (sentinel for pre-ingestion origin).

Request:
```json
{ "book_title": "Crime and Punishment", "author": "Fyodor Dostoevsky" }
```
Response: `BootstrapReport` — lists which sources succeeded, how many entries were seeded.

### POST `/{book_id}/ingest`
Run the agent loop on one book chunk. Call once per chunk, in order.

Internal flow:
1. Embed the chunk text
2. Fetch "Story So Far" cursor by title (always first — ordered context)
3. Semantic search for top-5 relevant wiki entries (cursor excluded)
4. Build context: `[narrative cursor] + [semantic results]`
5. Call LLM → parse JSON entries
6. Embed + upsert each entry

Request:
```json
{
  "chunk_text": "...",
  "chunk_index": 0,
  "book_title": "Crime and Punishment",
  "total_chunks": 120
}
```
Response: `IngestChunkResponse` — upserted entry IDs, retrieved count.

### GET `/{book_id}/wiki`
List all wiki entries. Filter: `?entry_type=character|theme|setting|plot|terminology|summary`

### POST `/{book_id}/wiki/search`
Semantic search via cosine similarity.
```json
{ "query": "who is Raskolnikov's sister", "top_k": 5 }
```

### DELETE `/{book_id}`
Delete all wiki entries for a book (irreversible).

### POST `/{book_id}/lint`
Run a targeted enrichment pass — detects gaps via keyword heuristics, then fires a focused LLM call per gap to fill only the missing fields:
- **character**: `speech_patterns`, `personality_traits`, `relationships`, `narrative_arc`
- **plot**: `characters_involved`, `consequence`
- **theme**: `textual_evidence`

Designed as a background job after ingestion is complete. Powers the reader-facing knowledge base product.

### GET `/{book_id}/export`
Export the full wiki as a Markdown string. Upload result to R2 at `bookbrain/{book_id}/wiki.md`.

---

## Key Design Decisions

### Narrative Cursor ("Story So Far")
The agent MUST produce a `summary` entry titled `"Story So Far"` on every chunk. This is the Karpathy index file — a running chronological narrative injected at the top of every subsequent chunk's context. Gives the LLM ordered temporal awareness without re-reading raw text. Retrieved by exact title match (not semantic search) to guarantee it's always present.

### Bootstrap as a Parallel Call
From `pdf-processor`, call `trigger_bookbrain_bootstrap()` alongside PDF extraction — not after it. The book title and author are known the moment the job is created. This gives BookBrain a ~15-20s head start to seed the wiki before the first chunk arrives.

Wire it like this (alongside your existing extraction task):
```python
from app.services.pipeline_client import trigger_bookbrain_bootstrap

bootstrap_task, pdf_task = await asyncio.gather(
    trigger_bookbrain_bootstrap(
        book_id=backend_book_id,
        book_title=title,
        author=author,
    ),
    your_pdf_extraction_coroutine(...),
)
```

### Source Chunk Index = -1
Bootstrap entries use `source_chunk_indices=[-1]` as a sentinel. The ingest loop uses `$addToSet` on upserts, so when the real text later enriches a character entry, the index list becomes `[-1, 3, 7, 12]` — you can see it was bootstrapped and which chunks updated it.

### MongoDB Storage
- Collection: `bookbrain_wiki`
- Index: `(book_id, entry_type, title)` — non-unique (title case normalization handled in upsert filter via `$regex`)
- Cosine similarity: in-memory Python (fine ≤5000 entries/book; swap for Atlas `$vectorSearch` at scale — zero schema changes)

### LLM Presets
- Text: `chat-knowledge` (gpt-oss-120b, 128k ctx) — best for literary analysis
- Embed: `embedding-768` (embeddinggemma-300m, CF) — matches voice_library pattern

---

## Testing Guide

### 0. Speed & Correctness Benchmark (show this to the team)

```bash
cd microservices/ai-service

# Full benchmark — Iron Letter mock book, all 6 phases (~90s)
python -m tests.bookbrain.benchmark

# Include a real-book bootstrap test (shows live internet data being compiled)
python -m tests.bookbrain.benchmark --real-book "Crime and Punishment" --author "Fyodor Dostoevsky"

# Fast iteration — skip bootstrap (~15s) and lint (~40s)
python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint
```

Produces both formatted console output and `tests/bookbrain/BENCHMARK_REPORT.md` — a shareable markdown file with tables, pass/fail indicators, timing data, character detection matrix, and search latency stats.

A pre-filled sample report is already at `tests/bookbrain/BENCHMARK_REPORT.md`. Run the script to overwrite it with live results.

---

### 1. Unit Tests — Linter (no DB, no LLM, runs in milliseconds)

```bash
cd microservices/ai-service
python -m pytest tests/bookbrain/test_linter.py -v
```

**What's tested:**
- `_find_missing_fields()` — gap detection heuristic (7 cases: all missing, none missing, partial, plot, theme, setting/terminology pass-through)
- `BookBrainLinter.lint()` — orchestration: skips complete entries, enriches gapped entries, handles multi-type wikis
- Edge cases: LLM failure → `was_enriched=False`, empty content → no upsert, empty wiki → clean zero-count report

**Expected output:** 9 tests, all green.

---

### 2. End-to-End Demo (against live ai-service, no real book needed)

Requires ai-service running locally (`python main.py` from `microservices/ai-service/`).

```bash
cd microservices/ai-service

# Full demo — all 6 phases
python -m tests.bookbrain.demo_bookbrain

# Reset wiki first, then run
python -m tests.bookbrain.demo_bookbrain --reset

# Search only (wiki must already be populated)
python -m tests.bookbrain.demo_bookbrain --search-only

# Skip ingest (if you already ingested)
python -m tests.bookbrain.demo_bookbrain --ingest-only
```

**The 6 demo phases:**
1. Health check
2. Narrative cursor inspection (Story So Far after all chunks)
3. Wiki contents by type
4. Semantic search (3 queries)
5. Alias map (character → canonical name)
6. Export + chunker integration summary

The demo uses a fictional book "The Iron Letter" (BOOK_ID = `demo-iron-letter-001`, 6 chunks) — completely isolated, no real book data needed.

---

### 3. Manual API Testing — Bootstrap

Requires ai-service running + valid `TAVILY_API_KEY` in `.env`.

```bash
# Seed wiki for a real book (fires all 4 sources concurrently)
curl -X POST http://localhost:8000/api/v1/bookbrain/test-book-001/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"book_title": "Crime and Punishment", "author": "Fyodor Dostoevsky"}'

# Expected response shape:
# {
#   "book_id": "test-book-001",
#   "book_title": "Crime and Punishment",
#   "sources_queried": ["tavily", "wikipedia", "openlibrary", "gutenberg"],
#   "sources_succeeded": ["tavily", "wikipedia", "openlibrary", "gutenberg"],
#   "entries_seeded": 12,
#   "duration_seconds": 18.4
# }

# Check what was seeded
curl http://localhost:8000/api/v1/bookbrain/test-book-001/wiki

# Check character entries specifically
curl "http://localhost:8000/api/v1/bookbrain/test-book-001/wiki?entry_type=character"

# Clean up
curl -X DELETE http://localhost:8000/api/v1/bookbrain/test-book-001
```

**What to verify:**
- `sources_succeeded` should include at least Wikipedia and Tavily for any well-known book
- Gutenberg succeeds only for public domain books (pre-1928)
- Character entries should have stubs for major characters
- Theme entries should reflect the book's known major themes

**Testing graceful degradation:**
- Temporarily set `TAVILY_API_KEY=invalid` in `.env` — Tavily should fail silently, other sources should still work
- Try an obscure/unknown book — some sources will return nothing; `entries_seeded` may be 0; this is correct behavior

---

### 4. Manual API Testing — Ingest Loop

```bash
# Ingest a test chunk
curl -X POST http://localhost:8000/api/v1/bookbrain/test-book-001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_text": "Raskolnikov stood at the door of the pawnbroker, rehearsing his plan.",
    "chunk_index": 0,
    "book_title": "Crime and Punishment",
    "total_chunks": 120
  }'

# Check the narrative cursor was created
curl "http://localhost:8000/api/v1/bookbrain/test-book-001/wiki?entry_type=summary"

# Semantic search
curl -X POST http://localhost:8000/api/v1/bookbrain/test-book-001/wiki/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Raskolnikov plan", "top_k": 3}'
```

---

### 5. Manual API Testing — Lint

```bash
# Run lint pass (after some chunks ingested — works best after full ingestion)
curl -X POST http://localhost:8000/api/v1/bookbrain/test-book-001/lint

# Expected response shape:
# {
#   "book_id": "test-book-001",
#   "entries_checked": 24,
#   "entries_enriched": 8,
#   "gaps": [...],
#   "duration_seconds": 42.1
# }
```

**What to verify:**
- `entries_checked` = total wiki entries for the book
- `entries_enriched` = subset that had keyword gaps AND were successfully filled
- Each gap has `missing_fields` (the heuristic-detected gaps) and `was_enriched: true/false`
- Settings and terminology entries should never appear in `gaps`

---

### 6. pdf-processor Integration (when ready to wire)

The `trigger_bookbrain_bootstrap()` function in `pipeline_client.py` is ready to drop in.

**Required env var in pdf-processor `.env`:**
```
AI_SERVICE_BASE_URL=http://127.0.0.1:8000/api/v1
```

**How to call (parallel with PDF extraction):**
```python
from app.services.pipeline_client import trigger_bookbrain_bootstrap

# Fire bootstrap in parallel — it does NOT need to complete before extraction
bootstrap_task = asyncio.create_task(
    trigger_bookbrain_bootstrap(
        book_id=backend_book_id,
        book_title=job.title,
        author=job.author,   # pass if available
    )
)
# ... continue with PDF extraction ...
# bootstrap runs in the background; log the result when convenient
```

**To test the trigger in isolation:**
```python
import asyncio
from app.services.pipeline_client import trigger_bookbrain_bootstrap

async def test():
    result = await trigger_bookbrain_bootstrap(
        book_id="test-001",
        book_title="1984",
        author="George Orwell",
    )
    print(result)

asyncio.run(test())
```

---

## Pending Next Steps

1. **Wire `trigger_bookbrain_bootstrap()` into pdf-processor job start** — find the point where `backend_book_id` + `title` + `author` are first known and fire the parallel task

2. **Wire BookBrain → SpeakerChunker character discovery** — in `llm_speaker_chunker.py`, replace lines 595-612 in `_discover_characters()` with a BookBrain wiki query: try `GET /{book_id}/wiki?entry_type=character` first, fall back to LLM if empty or wiki not yet populated

3. **Remove `breakpoint()` at line 604** in `llm_speaker_chunker.py` before any team demo

4. **Two-mode architecture (future):**
   - *Servant mode*: parallel entity extraction from all chunks concurrently (no narrative cursor) — for SpeakerChunker speed
   - *Product mode*: hierarchical narrative merge (background, sequential) — for reader-facing wiki

5. **ARQ job for lint** — wire `POST /{book_id}/lint` as an ARQ background job that fires after all chunks are ingested; prevents the 30-60s lint pass from blocking anything

---

## Env Vars Required

**ai-service `.env`:**
```
TAVILY_API_KEY=tvly-...     # already present
```

**pdf-processor `.env` (NEW):**
```
AI_SERVICE_BASE_URL=http://127.0.0.1:8000/api/v1
```
