# ADR-001: Narration Pipeline Orchestration

**Status:** Accepted  
**Date:** 2026-05-11  
**Authors:** Andrew D'Angelo

## Context

After the pdf-processor extracts text and calls `POST /internal/conversion/complete`, the
book record is created with `audio_url: null`. No service currently invokes TTS or uploads
audio to R2.

We need one clear orchestrator to execute: text chunks → TTS `/batch` → audio artifact in R2 → book record updated.

## Decision

**Option X — pdf-processor orchestrates TTS** (chosen for fewer moving parts at this stage).

After extraction completes, the pdf-processor:

1. Downloads the processed text JSON from R2.
2. Splits into TTS-sized chunks.
3. Calls the TTS service `POST /api/v1/tts/tts_processor/batch` with the default `voice_id`.
4. Receives audio segments, stitches into a single MP3.
5. Uploads the MP3 to R2.
6. Calls `PATCH /internal/books/{book_id}/audio` on the backend to persist `audio_url` and `duration`.

The backend exposes the new internal patch route (authenticated via `X-Internal-Service-Key`).
The frontend polls for `narration_status` on the book document until audio is available.

## Consequences

- Long-running TTS stays inside the existing BackgroundTasks pattern that pdf-processor
  already uses for PDF extraction. If TTS latency becomes a bottleneck, we can migrate to
  Option Y (backend-owned narration queue) without changing the internal API contract.
- Default voice is `DEFAULT_BASIC_VOICE_ID` from environment; UI voice selection (D7) is
  follow-up work that feeds into this same pipeline.

## Default Voice Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `DEFAULT_BASIC_VOICE_ID` | `alloy` | Voice used when user hasn't selected one |
