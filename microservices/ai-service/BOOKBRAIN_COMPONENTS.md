# BookBrain — Component Testing Guide

> System description, input/output contracts, and test commands for every component.  
> Service: `microservices/ai-service` · Port 8000 (local dev)

---

## System Overview

```
                        ┌─────────────────────────────────────┐
                        │          pdf-processor               │
                        │  trigger_bookbrain_bootstrap()       │
                        │  (fire-and-forget, parallel with PDF)│
                        └──────────────┬──────────────────────┘
                                       │ POST /bootstrap
                                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   ai-service /bookbrain                       │
│                                                               │
│  ┌─────────────┐     ┌──────────────┐    ┌───────────────┐   │
│  │  Bootstrap  │────▶│  WikiStore   │◀───│  Ingest Agent │   │
│  │  (4 sources)│     │  (MongoDB)   │    │  (per chunk)  │   │
│  └─────────────┘     │              │    └───────────────┘   │
│                       │  ┌─────────┐│                         │
│  ┌─────────────┐      │  │entries  ││    ┌───────────────┐   │
│  │   Linter    │◀────▶│  │embeddings│◀───│  Semantic     │   │
│  │ (background)│      │  │narrative │    │  Search       │   │
│  └─────────────┘      │  │cursor   ││    └───────────────┘   │
│                       │  └─────────┘│                         │
│  ┌─────────────┐      └──────────────┘   ┌───────────────┐   │
│  │  Markdown   │◀────────────────────────│    Export     │   │
│  │  Export     │                         └───────────────┘   │
│  └─────────────┘                                              │
└──────────────────────────────────────────────────────────────┘
         │ entries / search results
         ▼
  SpeakerChunker (pdf-processor)
  Reader-facing knowledge base product
```

### Data transformation at a glance

```
External sources (web, Wikipedia, OpenLibrary, Gutenberg)
        │ Bootstrap
        ▼
WikiEntry stubs  ──────────────────────────────────────────┐
        │                                                   │
Raw book chunks                                            │
        │ Ingest Agent (per chunk)                         │
        ▼                                                   │
WikiEntry  ─── embed ─── upsert ──────────────────────────▶│
        │                                                   │
        │ (narrative cursor always fetched first)           │
        ▼                                                   ▼
context prompt → LLM → parsed entries              MongoDB "bookbrain_wiki"
                                                           │
                               Linter ◀────────────────────┤
                               (gap detection → enrich)     │
                                                           │
                               Semantic Search ◀───────────┤
                               (cosine similarity)          │
                                                           │
                               Markdown Export ◀───────────┘
                               (grouped by type)
```

---

## Component 1 — Bootstrap

**File:** `app/bookbrain/bootstrap.py`  
**Class:** `BookBrainBootstrap`  
**Purpose:** Seeds the wiki with externally-sourced knowledge *before* any book chunks
are ingested. Runs as a parallel call alongside PDF extraction so the ingest agent
has character stubs and setting context from chunk 0 onward.

### Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `book_id` | `str` | ✅ | Unique identifier for the book (matches the ingest loop) |
| `book_title` | `str` | ✅ | Book title used for all 4 search queries |
| `author` | `str` | ✗ | Author name — improves Tavily, OpenLibrary, and Gutenberg hit rates |

**HTTP request body** (`POST /{book_id}/bootstrap`):
```json
{
  "book_title": "Crime and Punishment",
  "author": "Fyodor Dostoevsky"
}
```

### Internal steps

```
1. asyncio.gather → fire all 4 fetchers concurrently
   ├─ _fetch_tavily()      4 parallel Tavily searches (characters / themes / plot / analysis)
   ├─ _fetch_wikipedia()   REST summary API → extract field
   ├─ _fetch_openlibrary() search.json → work .json (description, subjects, year)
   └─ _fetch_gutenberg()   gutendex.com → optional opening 3 000 chars of plaintext

2. Collect results — any failure is silently skipped

3. If any source returned text:
   → _compile_and_upsert()
      └─ chat_json(system=_COMPILE_SYSTEM, user=gathered_text)
         → parse entries[] array
         → for each entry: generate_embedding() → upsert_entry(source_chunk_indices=[-1])
```

### Outputs

**`BootstrapReport`** schema:

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | `str` | The book identifier |
| `book_title` | `str` | Title that was searched |
| `sources_queried` | `List[str]` | Always `["tavily","wikipedia","openlibrary","gutenberg"]` |
| `sources_succeeded` | `List[str]` | Which sources returned usable text |
| `entries_seeded` | `int` | How many wiki entries were upserted |
| `duration_seconds` | `float` | Wall-clock time for the full pass |

**Example response:**
```json
{
  "book_id": "book-001",
  "book_title": "Crime and Punishment",
  "sources_queried": ["tavily", "wikipedia", "openlibrary", "gutenberg"],
  "sources_succeeded": ["tavily", "wikipedia", "openlibrary"],
  "entries_seeded": 12,
  "duration_seconds": 18.4
}
```

### Bootstrap entry marker

All seeded entries have `source_chunk_indices: [-1]` — the sentinel value meaning
"seeded before ingestion." When the ingest loop later upserts the same character,
the index list becomes `[-1, 3, 7]` so you can see which chunks confirmed the entry.

### How to test

```bash
# Manual — any well-known book
curl -X POST http://localhost:8000/api/v1/bookbrain/test-001/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"book_title": "The Great Gatsby", "author": "F. Scott Fitzgerald"}'

# Verify entries were created
curl http://localhost:8000/api/v1/bookbrain/test-001/wiki

# Test graceful degradation — bad API key should still get Wikipedia + OpenLibrary
# (Temporarily set TAVILY_API_KEY=invalid in .env, restart service, rerun)

# Benchmark (includes bootstrap)
python -m tests.bookbrain.benchmark --real-book "Crime and Punishment" --author "Fyodor Dostoevsky"
```

### What to verify

- `sources_succeeded` contains at least `wikipedia` and `openlibrary` for any well-known book
- `entries_seeded > 0` for any book with Wikipedia coverage
- Entries in wiki have `entry_type` in `character | theme | setting`
- `entries_seeded == 0` is acceptable for obscure books — not a failure
- Re-running bootstrap on a populated wiki refines entries (upsert, not duplicate)

### Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `sources_succeeded: []` | All 4 sources timed out or returned nothing | Check network, verify `TAVILY_API_KEY` |
| `entries_seeded: 0` despite sources succeeding | LLM returned empty `entries[]` | Check `chat-knowledge` preset is configured |
| HTTP 500 | Unhandled exception in compile step | Check ai-service logs |

---

## Component 2 — Ingest Agent

**File:** `app/bookbrain/agent.py`  
**Class:** `BookBrainAgent`  
**Method:** `ingest_chunk(book_id, chunk_text, chunk_index, book_title, total_chunks)`  
**Purpose:** The core per-chunk loop. Processes one book chunk: retrieves context from
the wiki, calls the LLM to extract/update entries, embeds and upserts results.

### Inputs

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `book_id` | `str` | ✅ | Book identifier |
| `chunk_text` | `str` | ✅ | Raw text of the current chunk |
| `chunk_index` | `int` | ✅ | 0-based position in the book |
| `book_title` | `str` | ✗ | Included in the LLM prompt header |
| `total_chunks` | `int` | ✗ | Allows LLM to understand narrative position |

**HTTP request body** (`POST /{book_id}/ingest`):
```json
{
  "chunk_text": "Watson had rarely heard Holmes speak of women...",
  "chunk_index": 2,
  "book_title": "The Adventures of Sherlock Holmes",
  "total_chunks": 120
}
```

### Internal steps

```
1. generate_embedding(chunk_text)
   → 768-dim vector (CF embeddinggemma-300m)

2. get_narrative_cursor(book_id)
   → MongoDB find_one WHERE title ILIKE "story so far"
   → Returns None on first chunk (empty wiki)

3. search_by_embedding(query_embedding, exclude_titles=["Story So Far"])
   → Loads all embeddings for book into memory
   → Cosine similarity score for each
   → Returns top-5 by score

4. Build LLM prompt:
   [book header + chunk position]
   [Narrative Context] ← cursor always first
   [Relevant Wiki Entries] ← semantic results
   [Current Chunk Text]

5. chat_with_system(system=_SYSTEM_PROMPT, user=user_message)
   → Model: chat-knowledge (gpt-oss-120b, 128k ctx)
   → Returns JSON: {"entries": [...]}

6. _parse_entries(raw)
   → Handles clean JSON, markdown-fenced JSON, embedded objects

7. For each entry:
   generate_embedding(f"{title}: {content}")
   → upsert_entry(WikiEntry)

8. Warn if "Story So Far" missing from LLM output
```

### Outputs

**`IngestChunkResponse`** schema:

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | `str` | Book identifier |
| `chunk_index` | `int` | The chunk that was processed |
| `retrieved_entries` | `int` | How many wiki entries were pulled as context |
| `upserted_entries` | `int` | How many entries were written back |
| `wiki_entry_ids` | `List[str]` | UUIDs of upserted entries |

**Example response:**
```json
{
  "book_id": "book-001",
  "chunk_index": 2,
  "retrieved_entries": 4,
  "upserted_entries": 6,
  "wiki_entry_ids": ["a1b2c3...", "d4e5f6...", "..."]
}
```

### Narrative cursor — the ordering mechanism

On every chunk, the agent:
1. Fetches "Story So Far" by **exact title regex** (not semantic search)
2. Injects it **first** in context — before semantic results
3. The LLM **must** return an updated "Story So Far" entry (enforced in system prompt)

This gives the LLM ordered temporal awareness without re-reading prior raw text.
The cursor is excluded from semantic search results to avoid double-injection.

### How to test

```bash
# Single chunk
curl -X POST http://localhost:8000/api/v1/bookbrain/book-001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "chunk_text": "It was a dark and stormy night...",
    "chunk_index": 0,
    "book_title": "Example Book",
    "total_chunks": 1
  }'

# Full 6-chunk mock book
python -m tests.bookbrain.demo_bookbrain --reset

# Gutenberg real text (8 chunks of Sherlock Holmes)
python -m tests.bookbrain.test_gutenberg_integration --reset

# Benchmark (phases 2 + 3)
python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint
```

### What to verify

- `upserted_entries >= 1` on every chunk (at minimum the cursor)
- After chunk 0: wiki contains a "summary" entry with `title="Story So Far"`
- `retrieved_entries` increases as the wiki grows (more context on later chunks)
- `chunk_index` increments correctly — out-of-order ingestion will confuse the narrative cursor

### Failure modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| `upserted_entries: 0` | LLM returned no parseable JSON | Check logs for `could not parse LLM output` warning |
| `"Story So Far" MISSING` warning in logs | LLM dropped mandatory cursor | Usually a prompt compliance issue with certain models |
| HTTP 500 on every chunk | Embedding service down | Check `MATT_CF_ACCOUNT_ID` + `MATT_CF_AI_TOKEN` |
| First chunk slow, rest fast | Cold-start on CF Workers AI | Normal — first embedding call warms the endpoint |

---

## Component 3 — Wiki Store

**File:** `app/bookbrain/wiki_store.py`  
**Class:** `BookBrainWikiStore`  
**Purpose:** All MongoDB read/write operations. The storage substrate — stateless,
called by every other component.

### Data model — `WikiEntry`

| Field | Type | DB behaviour |
|-------|------|-------------|
| `entry_id` | `str` (UUID) | `$setOnInsert` — preserved across updates |
| `book_id` | `str` | Filter key |
| `entry_type` | `str` (enum) | `character\|theme\|setting\|plot\|terminology\|summary` |
| `title` | `str` | Case-insensitive upsert key (regex match) |
| `content` | `str` | `$set` — replaced on every update |
| `embedding` | `List[float]` (768-dim) | `$set` — replaced on update |
| `source_chunk_indices` | `List[int]` | `$addToSet` — accumulates across updates |
| `created_at` | `datetime` | `$setOnInsert` — frozen after first insert |
| `updated_at` | `datetime` | `$set` — refreshed on every update |

**Index:** `(book_id, entry_type, title)` — non-unique (title normalization handled in upsert filter).

### Key methods

#### `upsert_entry(entry: WikiEntry) → str`

Insert-or-update by `(book_id, entry_type, title ILIKE title)`.  
Returns `entry_id`. Uses MongoDB `update_one(..., upsert=True)`.

Critical: `source_chunk_indices` uses `$addToSet` so re-processing a chunk never
duplicates indices. The entry grows its index list across multiple ingestion runs.

#### `get_narrative_cursor(book_id) → Optional[WikiEntryPublic]`

Fetches "Story So Far" by exact case-insensitive regex on title.
Always called before semantic search. Returns `None` on empty wiki.

#### `search_by_embedding(book_id, query_embedding, top_k, entry_type, exclude_titles) → List[Tuple[WikiEntryPublic, float]]`

Loads all embeddings for `book_id` into memory → pure-Python cosine similarity.  
`exclude_titles` prevents "Story So Far" from appearing in semantic results
(it is always injected separately as the narrative cursor).

**Scaling:** Fine to ~5,000 entries/book. At production scale, add an Atlas Vector
Search index on `embedding` and replace with `$vectorSearch` — zero schema changes.

#### `delete_book_wiki(book_id) → int`

Hard delete. Returns deleted count. Used for test cleanup and the DELETE endpoint.

#### `export_markdown(book_id) → str`

Renders all entries as grouped Markdown. Returns the full string — caller uploads
to R2 at `bookbrain/{book_id}/wiki.md`.

### How to test

```bash
# Inspect raw wiki contents via API
curl "http://localhost:8000/api/v1/bookbrain/book-001/wiki"

# Filter by type
curl "http://localhost:8000/api/v1/bookbrain/book-001/wiki?entry_type=character"

# Direct MongoDB inspection (mongosh)
use audiobooker_backend_db
db.bookbrain_wiki.find({ book_id: "book-001" }).pretty()
db.bookbrain_wiki.find({ book_id: "book-001" }).count()

# Check source_chunk_indices accumulation (shows -1 for bootstrapped, then real indices)
db.bookbrain_wiki.find(
  { book_id: "book-001", entry_type: "character" },
  { title: 1, source_chunk_indices: 1, _id: 0 }
)
```

### What to verify

- Each `(book_id, entry_type, title)` combination has exactly one document
- `source_chunk_indices: [-1]` on bootstrap entries before ingestion begins
- After ingestion, bootstrapped entries show `[-1, 3, 7, ...]` (merged history)
- `created_at` is stable across multiple upserts; `updated_at` advances
- Embedding field is present and has 768 elements (not null)

---

## Component 4 — Linter

**File:** `app/bookbrain/linter.py`  
**Class:** `BookBrainLinter`  
**Purpose:** Periodic background enrichment pass. Scans all wiki entries for missing
fields using fast keyword heuristics (no LLM), then fires a focused LLM call per gap
to fill only the absent sections. Designed to run once after full ingestion completes.

### Inputs

| Parameter | Type | Description |
|-----------|------|-------------|
| `book_id` | `str` | Reads all wiki entries for this book from MongoDB |

**HTTP call:** `POST /{book_id}/lint` (no body)

### Gap detection — `_find_missing_fields(entry)`

Pure-function keyword heuristic. No LLM, runs in microseconds per entry.

| Entry type | Field | Missing if content contains none of... |
|------------|-------|----------------------------------------|
| `character` | `speech_patterns` | speech, speaks, pattern, dialect, tone, voice, register, catchphrase |
| `character` | `personality_traits` | personality, trait, deceptive, honest, warm, cold, driven, fearful, arrogant, humble, cunning, loyal |
| `character` | `relationships` | relationship, ally, enemy, friend, rival, mentor, trusts, distrusts, loves, hates |
| `character` | `narrative_arc` | arc, change, growth, transforms, evolves, redeems, deteriorates, journey |
| `plot` | `characters_involved` | involves, character, who, protagonist, antagonist |
| `plot` | `consequence` | result, consequence, leads to, causes, aftermath, effect |
| `theme` | `textual_evidence` | for example, illustrated by, seen when, demonstrated, exemplified, such as |
| `setting`, `terminology`, `summary` | — | **Skipped entirely** — no gaps checked |

### Internal steps

```
1. store.get_entries(book_id) → all entries

2. For each entry:
   a. _find_missing_fields(entry) → list of missing field names
   b. If no gaps: skip

3. For each gapped entry:
   _enrich_entry(book_id, entry, missing_fields)
   └─ chat_json(system=_SYSTEM_BY_TYPE[entry_type], user=f"Missing: {fields}\n{content}")
      → {"missing_fields": [...], "enriched_content": "..."}
      → generate_embedding(enriched_content)
      → upsert_entry(updated WikiEntry)

4. Collect LintGap records (one per gapped entry)
5. Return LintReport
```

### Outputs

**`LintReport`** schema:

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | `str` | The book scanned |
| `entries_checked` | `int` | Total entries scanned |
| `entries_enriched` | `int` | How many were successfully enriched |
| `gaps` | `List[LintGap]` | One record per entry that had missing fields |
| `duration_seconds` | `float` | Wall-clock time |

**`LintGap`** fields: `entry_id`, `entry_type`, `title`, `missing_fields: List[str]`, `was_enriched: bool`

**Example response:**
```json
{
  "book_id": "book-001",
  "entries_checked": 22,
  "entries_enriched": 7,
  "gaps": [
    {
      "entry_id": "abc-123",
      "entry_type": "character",
      "title": "Raskolnikov",
      "missing_fields": ["speech_patterns", "narrative_arc"],
      "was_enriched": true
    }
  ],
  "duration_seconds": 38.4
}
```

### How to test

```bash
# Run lint (after some chunks ingested)
curl -X POST http://localhost:8000/api/v1/bookbrain/book-001/lint

# Unit tests — fully isolated (no service required, no LLM calls)
cd microservices/ai-service
python -m pytest tests/bookbrain/test_linter.py -v

# Benchmark (phase 5)
python -m tests.bookbrain.benchmark --skip-bootstrap
```

**Unit test coverage:**

| Test | What it verifies |
|------|-----------------|
| `test_character_all_missing` | Bare entry → all 4 fields flagged |
| `test_character_nothing_missing` | Complete entry → no gaps |
| `test_character_only_speech_missing` | Partial entry → correct field identified |
| `test_plot_entry_missing_consequence` | Plot gap detection |
| `test_theme_missing_evidence` | Theme gap detection |
| `test_setting_not_checked` | Setting entries are skipped |
| `test_terminology_not_checked` | Terminology entries are skipped |
| `test_skips_entries_with_no_gaps` | No LLM call when no gaps |
| `test_enriches_entry_with_gaps` | Correct content upserted |
| `test_multiple_entry_types_checked` | All 3 checked types processed |
| `test_llm_failure_marks_not_enriched` | Exception → `was_enriched: false` |
| `test_llm_empty_content_marks_not_enriched` | Empty response → no upsert |
| `test_empty_wiki_returns_clean_report` | Zero entries → valid report |

### What to verify

- `entries_checked` = total wiki entry count for the book
- Settings/terminology/summary entries never appear in `gaps`
- `was_enriched: false` when LLM fails — gap is recorded but wiki is unchanged
- Re-running lint on an already-enriched wiki: `entries_enriched: 0` (heuristics pass)

### Performance note

For a 900-page book (~40 character entries): expect 30–60s total. Each LLM call
fills 1–2 missing fields on one entry. Wire to an ARQ background job to avoid
blocking the API response.

---

## Component 5 — Semantic Search

**File:** `app/bookbrain/wiki_store.py` (`search_by_embedding`)  
**Endpoint:** `POST /{book_id}/wiki/search`  
**Purpose:** Retrieve the most contextually relevant wiki entries for a given query.
Used internally by the ingest agent for context building, and externally for the
reader-facing knowledge base API.

### Inputs

**`WikiSearchRequest`**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `query` | `str` | — | Natural language search query |
| `top_k` | `int` | `5` | Maximum entries to return |
| `entry_type` | `str` | `null` | Filter results to one entry type |

```json
{
  "query": "How does Holmes use disguises?",
  "top_k": 3,
  "entry_type": "character"
}
```

### Internal steps

```
1. generate_embedding(query)   → 768-dim query vector
2. search_by_embedding(book_id, query_embedding, top_k, entry_type, exclude_titles=[])
   → find all docs for book_id WHERE embedding IS NOT NULL
   → compute cosine(query_vec, entry_vec) for each
   → sort descending by score
   → return top_k
3. Return results + scores
```

### Outputs

**`WikiSearchResponse`**:

| Field | Type | Description |
|-------|------|-------------|
| `results` | `List[WikiEntryPublic]` | Top-k entries, ordered by score |
| `scores` | `List[float]` | Cosine similarity score (0–1) for each result |

**Example response:**
```json
{
  "results": [
    {
      "entry_id": "abc-123",
      "book_id": "book-001",
      "entry_type": "character",
      "title": "Sherlock Holmes",
      "content": "...",
      "source_chunk_indices": [-1, 0, 2, 5],
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "scores": [0.89]
}
```

### How to test

```bash
# Basic search
curl -X POST http://localhost:8000/api/v1/bookbrain/book-001/wiki/search \
  -H "Content-Type: application/json" \
  -d '{"query": "main character detective", "top_k": 5}'

# Type-filtered search
curl -X POST http://localhost:8000/api/v1/bookbrain/book-001/wiki/search \
  -H "Content-Type: application/json" \
  -d '{"query": "London setting", "top_k": 3, "entry_type": "setting"}'

# Benchmark (phase 4 — 5 queries with latency measurement)
python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint

# Gutenberg integration test (semantic validation)
python -m tests.bookbrain.test_gutenberg_integration --skip-bootstrap
```

### What to verify

- Top result for a character query should have `entry_type: "character"`
- Scores are between 0 and 1; relevant results typically score > 0.6
- `top_k` is respected — response `results` length ≤ `top_k`
- Empty wiki returns `{"results": [], "scores": []}`
- Filtering by `entry_type` narrows results correctly

---

## Component 6 — Markdown Export

**File:** `app/bookbrain/wiki_store.py` (`export_markdown`)  
**Endpoint:** `GET /{book_id}/export`  
**Purpose:** Render the entire wiki as a human-readable Markdown document, grouped by
entry type. Upload the result to R2 for cross-service access or reader display.

### Input

URL parameter: `book_id`

### Output

**`WikiExportResponse`**:

| Field | Type | Description |
|-------|------|-------------|
| `book_id` | `str` | The book exported |
| `markdown` | `str` | Full Markdown document (all entries, grouped by type) |
| `r2_key` | `Optional[str]` | Not yet set server-side — populate when uploading to R2 |

**Output structure:**
```markdown
# BookBrain Wiki: {book_id}

## Character

### Sherlock Holmes
[content]
*Sources: chunks [-1, 0, 2]*

### Dr. Watson
[content]
*Sources: chunks [-1, 0]*

## Theme
...
```

### How to upload to R2

```python
async with r2_session.client("s3", endpoint_url=settings.R2_ENDPOINT_URL, ...) as s3:
    await s3.put_object(
        Bucket=settings.R2_BUCKET_NAME,
        Key=f"bookbrain/{book_id}/wiki.md",
        Body=markdown.encode("utf-8"),
        ContentType="text/markdown",
    )
```

### How to test

```bash
# Export and display
curl http://localhost:8000/api/v1/bookbrain/book-001/export | python -m json.tool

# Check markdown is non-empty
curl -s http://localhost:8000/api/v1/bookbrain/book-001/export | jq '.markdown | length'

# Benchmark (phase 6 — measures export latency and output size)
python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint
```

---

## Component 7 — pdf-processor Pipeline Trigger

**File:** `microservices/pdf-processor/app/services/pipeline_client.py`  
**Function:** `trigger_bookbrain_bootstrap(book_id, book_title, author)`  
**Purpose:** Fire-and-forget HTTP call from pdf-processor to ai-service bootstrap endpoint.
Mirrors the existing `trigger_book_generation()` pattern. Failure never propagates.

### When to call

Immediately after `backend_book_id` + `book_title` + `author` are first known — before
PDF extraction starts, so bootstrap runs in parallel:

```python
bootstrap_task = asyncio.create_task(
    trigger_bookbrain_bootstrap(
        book_id=backend_book_id,
        book_title=job.title,
        author=job.author,
    )
)
# PDF extraction continues here — bootstrap runs concurrently
```

### Required env var (pdf-processor `.env`)

```
AI_SERVICE_BASE_URL=http://127.0.0.1:8000/api/v1
```

Default is already set to this value in `config_settings.py`.

### Inputs

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `book_id` | `str` | ✅ | Backend book UUID (same ID used for ingest later) |
| `book_title` | `str` | ✅ | Book title for external source queries |
| `author` | `str` | ✗ | Improves hit rates; pass `None` if unknown |

### Output

`Optional[dict]` — the `BootstrapReport` JSON if successful, `None` on any failure.
Failure is logged but never raised to the caller.

### How to test

```python
# Standalone test (run from microservices/pdf-processor/)
import asyncio
from app.services.pipeline_client import trigger_bookbrain_bootstrap

async def test():
    result = await trigger_bookbrain_bootstrap(
        book_id="test-trigger-001",
        book_title="The Great Gatsby",
        author="F. Scott Fitzgerald",
    )
    print(result)

asyncio.run(test())
```

```bash
# Verify the AI_SERVICE_BASE_URL is set
cd microservices/pdf-processor
python -c "from app.core.config_settings import settings; print(settings.AI_SERVICE_BASE_URL)"
```

---

## End-to-End Flow

Complete sequence from job creation to fully-enriched wiki:

```
1. pdf-processor receives book job (title, author, book_id known)
   │
   ├── asyncio.create_task(trigger_bookbrain_bootstrap())  ─────────────┐
   │                                                                     │
   └── PDF extraction begins                                             │ ~20s concurrent
                                                                         │
2. Bootstrap completes ──────────────────────────────────────────────────┘
   → 10-15 wiki stubs seeded (characters, themes, settings)
   → source_chunk_indices: [-1] on all bootstrap entries

3. SpeakerChunker begins (or pdf-processor sends chunks to ingest)
   → POST /bookbrain/{book_id}/ingest  (chunk 0)
      - Wiki has bootstrap stubs → retrieved_entries > 0 even on chunk 0
      - LLM confirms / expands character stubs from actual text
      - "Story So Far" cursor created
   → POST /bookbrain/{book_id}/ingest  (chunk 1 ... N)
      - Cursor always injected first (ordered context)
      - Semantic search surfaces relevant existing entries
      - Each chunk adds / refines entries; cursor updated

4. All chunks ingested
   → POST /bookbrain/{book_id}/lint  (background job / ARQ)
      - Gap detection: which character entries lack speech_patterns, etc.
      - LLM fills only the missing fields
      - Wiki is now fully enriched

5. GET /bookbrain/{book_id}/export
   → Upload markdown to R2 at bookbrain/{book_id}/wiki.md
   → Surface to reader as interactive knowledge base

6. SpeakerChunker uses wiki for dialogue attribution:
   → GET /wiki?entry_type=character  →  verified character list + aliases
   → POST /wiki/search  →  context for ambiguous dialogue attribution
```

---

## Test Matrix

| Test command | Coverage | Requires service? | Duration |
|---|---|---|---|
| `pytest tests/bookbrain/test_linter.py -v` | Linter gap detection + enrichment | ❌ No (fully mocked) | ~1s |
| `python -m tests.bookbrain.demo_bookbrain --reset` | Full ingest + search + export (Iron Letter) | ✅ Yes | ~3 min |
| `python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint` | Ingest speed + search latency + wiki quality | ✅ Yes | ~3 min |
| `python -m tests.bookbrain.benchmark` | All 7 phases including bootstrap and lint | ✅ Yes | ~6 min |
| `python -m tests.bookbrain.benchmark --real-book "..." --author "..."` | Bootstrap against a real book | ✅ Yes + internet | ~7 min |
| `python -m tests.bookbrain.test_gutenberg_integration --reset` | Real Gutenberg text — full pipeline | ✅ Yes + internet | ~5 min |
| `pytest tests/bookbrain/test_gutenberg_integration.py -v -s -m integration` | Same, as pytest assertions | ✅ Yes + internet | ~5 min |

### Quick smoke test sequence (post-deploy)

```bash
cd microservices/ai-service

# 1. Unit tests first (no service needed)
python -m pytest tests/bookbrain/test_linter.py -v

# 2. Start the service
python main.py &

# 3. Fast integration check (no bootstrap, no lint — ~3 min)
python -m tests.bookbrain.benchmark --skip-bootstrap --skip-lint

# 4. Full benchmark before team demo
python -m tests.bookbrain.benchmark \
  --real-book "Crime and Punishment" \
  --author "Fyodor Dostoevsky"
# → generates BENCHMARK_REPORT.md

# 5. Gutenberg real-book validation
python -m tests.bookbrain.test_gutenberg_integration --reset
```

---

## Schemas — Quick Reference

```python
# Entry types (used as exact strings in API and DB)
character | theme | setting | plot | terminology | summary

# WikiEntry (DB write shape — includes embedding)
WikiEntry(entry_id, book_id, entry_type, title, content,
          embedding: List[float],           # 768-dim
          source_chunk_indices: List[int],  # [-1] = bootstrap; [0,3,7] = ingest
          created_at, updated_at)

# WikiEntryPublic (API response shape — embedding excluded)
WikiEntryPublic(entry_id, book_id, entry_type, title, content,
                source_chunk_indices, created_at, updated_at)

# LLM call signatures
AITextService.chat_with_system(system, user, provider, preset)  → str
AITextService.chat_json(prompt_messages, provider, preset)       → dict
AIEmbeddingService.generate_embedding(text, provider, preset)    → List[float]

# Model presets
text  → preset="chat-knowledge"  (gpt-oss-120b, 128k ctx)
embed → preset="embedding-768"   (embeddinggemma-300m, CF, 768-dim)
```

---

*Last updated: 2026-05-18 — covers bootstrap, ingest agent, wiki store, linter, semantic search, export, and pipeline trigger.*
