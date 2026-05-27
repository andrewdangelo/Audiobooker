# Claude Checkpoint — May 11, 2026 18:00
## Audiobooker — TTS Pipeline Session Summary

This file is a handoff checkpoint from a claude.ai conversation. Use it to pick up where we left off.
Tell Claude: "Read claude_checkpoint_5_11_26_1800.md and continue from where we left off."

---

## Project Overview

Microservices-based audiobook generation platform. You own **ai-service** and **tts-infrastructure**.
Other services (backend, pdf-processor, auth-service, payment-service) are owned by other engineers — be additive and careful when touching them.

**Stack:** Python, FastAPI, MongoDB, Cloudflare R2, HuggingFace Inference Endpoints, Redis, ARQ

**Ports (local dev):**
- ai-service: 8000
- tts-infrastructure: 8003
- pdf-processor: 8001
- backend: 8002

**Redis:** Runs as a native Windows service on 127.0.0.1:6379 (not WSL). Always use `127.0.0.1` not `localhost` — ARQ/some clients resolve localhost to IPv6 on this machine.

---

## What We Built This Session

### The Core Pipeline (NEW)
The main gap we closed: pdf-processor finishes → tts-infrastructure picks up and generates audio chunks.

**Full flow:**
```
pdf-processor
  → POST tts-infrastructure/api/v1/tts/book-generation/start
  → ARQ worker picks up job
  → downloads script JSON from R2
  → voice assignment (once, against characters[])
  → downloads voice WAVs (once per unique voice_id)
  → warmup TTS model
  → concurrent TTS loop (semaphore=5)
  → uploads chunk WAVs to R2
  → job marked completed
```

### New Files Created

**tts-infrastructure/app/services/book_generation_service.py** (NEW)
- Full async job loop
- Redis job tracking (same pattern as pdf-processor)
- Two data structures: `assignment_map {character_name: voice_id}` and `voice_cache {voice_id: bytes}`
- Assignment happens ONCE against `script["characters"]` — never per-chunk
- Concurrent TTS with `asyncio.Semaphore(TTS_CONCURRENCY=5)`
- Progress reporter runs as `asyncio.create_task` (not inside gather — avoids deadlock)
- Result schema: `chunks: {succeeded: [r2_keys], failed: [indices], skipped: [indices]}`
- Warmup step (3.5) before loop — calls ai-service /internal/tts/warmup

**tts-infrastructure/app/routers/book_generation.py** (NEW)
- `POST /start` — enqueues ARQ job, returns job_id (202)
- `GET /job/{job_id}` — poll status
- `GET /jobs` — debug list
- `JobStatusResponse` has live counters for polling + typed `GenerationResult` on completion
- `_int_or_none()` helper — never coerces 0 to None (0 is meaningful, None means absent)

**tts-infrastructure/worker.py** (NEW)
- ARQ worker entrypoint
- `WorkerSettings`: max_jobs=1, job_timeout=3600, retry_jobs=True, max_tries=2
- Start with: `python worker.py` in a third terminal
- Redis must be running before starting worker

**ai-service/app/routers/internal_tts.py** (NEW)
- `POST /internal/tts/warmup` — wakes HF endpoint, blocks until ready
- `POST /internal/tts/generate-chunk` — voice bytes + text → WAV bytes
- `POST /internal/voice-library/assign-single` — returns random standard voice_id
- All endpoints require `X-Internal-Service-Key` header

### Modified Files

**tts-infrastructure/main.py**
- Added ARQ pool creation on startup: `app.state.arq_pool = await arq.create_pool(...)`
- Added `book_generation.router` at prefix `/api/v1/tts/book-generation`
- Removed WSL redis-start command (Redis runs as Windows service, not WSL)

**tts-infrastructure/app/core/config_settings.py**
- Added `AI_SERVICE_BASE_URL: str`
- Added `INTERNAL_SERVICE_KEY: str`
- Fixed `API_V1_PREFIX` — was `/api/v1/pdf` (wrong), should be `/api/v1/tts`

**ai-service/app/services/ai_speech_service.py**
- Replaced `_model_cache: dict[str, HFTTSClient]` with `_endpoint_url_cache: dict[str, str]`
- Caches URL only (never goes stale), constructs fresh HFTTSClient per call
- Added `_init_lock: asyncio.Lock` with double-checked locking pattern
- Added `warmup()` classmethod

**ai-service/app/services/ai_hf_clients.py**
- Fixed `base64.b64encode(voice_sample_bytes)` → `.decode()` (was returning bytes, not str)
- HF endpoint returns `{"generated_audio": "<base64>"}` — decode with `base64.b64decode(response.json()["generated_audio"])`
- Added retry loop on 503 (cold start): max_retries=5, retry_delay=30s
- Added retry on ReadTimeout with same params
- Timeout: 300s (was default 5s — way too low for TTS inference)

**ai-service/app/routers/voice_library.py**
- Added `GET /voice-library/voices` — list all, `?standard_only=true` filter, embeddings excluded
- Added `PATCH /voice-library/voices/{voice_id}` — flip `is_standard` without re-uploading
- Added `DELETE /voice-library/voices` — nuke all (loops delete_voice_by_id for R2 cleanup)
- Note: `DELETE /voices` defined BEFORE `DELETE /voices/{voice_id}` — FastAPI route order matters

**ai-service/main.py**
- Added `internal_tts.router` at prefix `{API_V1_PREFIX}/internal`
- Added lifespan context manager for VoiceLibraryManager init

**pdf-processor/app/services/pipeline_client.py**
- Added `trigger_book_generation()` — POSTs to tts-infrastructure after backend book creation
- Fire-and-forget: failure does not fail the pdf-processor job

**pdf-processor/app/services/pdf_processor_service.py** (PATCH — not full replacement)
- Add import: `from app.services.pipeline_client import ... trigger_book_generation`
- Insert after backend_book_id confirmed, before final update_job:
  ```python
  if script_output_key:
      await trigger_book_generation(
          book_id=backend_book_id,
          script_r2_key=script_output_key,
          user_id=user_id,
      )
  ```

**pdf-processor/app/core/config_settings.py** (PATCH)
- Add: `TTS_SERVICE_BASE_URL: str = Field(default="http://127.0.0.1:8003/api/v1/tts")`

**ai-service/app/core/config_settings.py** (PATCH)
- Add: `INTERNAL_SERVICE_KEY: str = Field(...)`

### New Test Files

**tts-infrastructure/tests/unit/test_book_generation_concurrency.py** (NEW)
- 4 tests, all passing
- test_semaphore_caps_concurrency — high water mark never exceeds TTS_CONCURRENCY
- test_results_written_by_index — correct index regardless of completion order
- test_failed_chunks_isolated — failures don't poison neighbours
- test_empty_lines_skipped — skipped != failed

**ai-service/tests/seed_standard_voices.py** (NEW)
- Clears MongoDB voice_library collection
- Clears R2 voice_library/ prefix
- Re-seeds from tests/voice_samples/*.wav via full add_voice() pipeline
- Controls is_standard via STANDARD_VOICES set at top of file
- Run: `python -m tests.seed_standard_voices`

**tts-infrastructure/upload_smoke_script.py** (NEW)
- Uploads 3-line test script to R2 at `processed_audiobooks/smoke_test_script.json`
- Uses settings object (no hardcoded creds)
- Run: `python upload_smoke_script.py`

---

## Key Architecture Decisions

**Voice assignment:** Settled ONCE against `script["characters"]` list before the TTS loop.
Never per-chunk. Two maps:
- `assignment_map: {character_name: voice_id}` — stable for entire book
- `voice_cache: {voice_id: bytes}` — WAV bytes downloaded once per unique voice_id

**Result schema for chunks:**
```json
"chunks": {
  "succeeded": ["audiobook_chunks/{book_id}/0.wav", ...],  // full R2 keys
  "failed": [2, 5],     // indices only (no R2 key was written)
  "skipped": [7]        // indices only (empty text, TTS not attempted)
}
```
Full R2 keys for succeeded (consumers need them directly), indices for failed/skipped.

**Semaphore:** `TTS_CONCURRENCY = 5` in book_generation_service.py. Tune against HF endpoint capacity. Start at 5, increase until 429s appear, back off one step.

**ARQ vs BackgroundTasks:** ARQ chosen for durability — job survives uvicorn restart. Worker is separate process. Three terminals to run locally: ai-service, tts-infrastructure, worker.

**Redis connection:** Always `127.0.0.1` not `localhost` on this machine. localhost resolves to IPv6 (::1) on Windows, Redis is bound to IPv4 only.

**Internal service auth:** `X-Internal-Service-Key` header, same value in all services' .env. One shared secret — mutual recognition, not per-service keys.

**Cache strategy for HF client:** Cache endpoint URL (string, never stale). Construct fresh HFTTSClient per call. `_init_lock` with double-checked locking prevents concurrent cold-start races.

**ModelFactory._ensure_endpoint_is_ready:** Only call `endpoint.resume()` on `scaledToZero` or `paused` — NOT `pending` (already waking up). HF returns 400 if you try to resume a non-stopped endpoint.

---

## .env Keys Required

**tts-infrastructure/.env:**
```
API_V1_PREFIX=/api/v1/tts
PORT=8003
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
AI_SERVICE_BASE_URL=http://127.0.0.1:8000/api/v1/ai_service
INTERNAL_SERVICE_KEY=<shared secret>
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
```

**ai-service/.env:**
```
API_V1_PREFIX=/api/v1/ai_service
PORT=8000
INTERNAL_SERVICE_KEY=<same shared secret>
HF_TOKEN=...
HF_WRITE_TOKEN=...
MONGODB_URL=...
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=...
```

---

## R2 Storage Layout

```
voice_library/{voice_id}.wav                          ← voice samples
processed_audiobooks/{job_id}_processed.json          ← raw text chunks (pdf-processor)
processed_audiobooks/{job_id}_script.json             ← speaker-attributed script (pdf-processor)
audiobook_chunks/{book_id}/{chunk_index}.wav          ← generated TTS chunks (tts-infrastructure)
audiobook_final/{book_id}/final.mp3                   ← stitched output (NOT YET BUILT)
```

---

## What's Next (Immediate)

### 1. Audio Stitching (next up)
Take the chunk WAVs from `audiobook_chunks/{book_id}/*.wav` and stitch into a final MP3.
tts-infrastructure already has `AudioStitcher` built but it expects local file paths, not R2 keys.
Options:
- (a) Add R2 download step to tts-infrastructure AudioStitcher
- (b) Do stitching directly in book_generation_service using pydub after chunks complete

Trigger stitching at end of `run_book_generation()` after step 6, or as a separate job.
Output goes to R2 at `audiobook_final/{book_id}/final.mp3`.

### 2. Write audio_url back to backend
After stitching, call backend internal endpoint to update the book record.
Needs: `PATCH /api/v1/internal/books/{book_id}/audio` on backend's `internal.py` router.
Payload: `{audio_url, duration, chapters[]}`.
This is what makes the audiobook playable from the frontend.

### 3. Prod improvements (documented, not urgent)
- ARQ resume logic: store completed chunk indices, resume from last checkpoint
- Chunk state to MongoDB instead of Redis (survives TTL expiry)
- HF endpoint health cron (keep warm, avoid cold starts)
- Per-character voice assignment (phase 2 — assign_voice_multiple)

---

## Known Issues / Watch Out For

- `breakpoint()` exists in `pdf-processor/app/services/llm_speaker_chunker.py` inside `_discover_characters()` — remove before enabling `ENABLE_LLM_CHUNKING=true`
- auth-service has dual DB strategy (Postgres + Mongo) — check which is primary before touching
- backend `analytics.router` is commented out in main.py
- `tts-infrastructure` lifespan cleanup for old stitching jobs is commented out
- Pydantic V1 style validators in config_settings.py across all services — deprecated warnings, not breaking, low priority

---

## Smoke Test (Quick Reference)

```bash
# Terminal 1
cd microservices/ai-service && python main.py

# Terminal 2
cd microservices/tts-infrastructure && python main.py

# Terminal 3
cd microservices/tts-infrastructure && python worker.py
```

1. Seed voices if needed: `python -m tests.seed_standard_voices` (from ai-service root)
2. Upload smoke script: `python upload_smoke_script.py` (from tts-infrastructure root)
3. Hit `POST /api/v1/tts/book-generation/start` on tts-infrastructure /docs (port 8003):
```json
{
  "book_id": "11111111-1111-1111-1111-111111111111",
  "script_r2_key": "processed_audiobooks/smoke_test_script.json",
  "user_id": "test-user-001"
}
```
4. Poll `GET /api/v1/tts/book-generation/job/{job_id}` until `status: completed`
5. Verify 3 WAV files in R2 under `audiobook_chunks/11111111.../`