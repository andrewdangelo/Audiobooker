# ADR-001: TTS narration orchestrator lives in pdf-processor (Option X)

**Status:** Accepted  
**Date:** 2026-05-11

## Context

After text extraction completes, the system needs to synthesize narration audio
(single voice for basic-tier) and persist the resulting file so the book's
`audio_url` field points to a real asset.

Two options were considered:

- **Option X** — Extend `pdf-processor`: after extraction, call TTS `/batch`,
  upload audio to R2, then PATCH the backend book via the internal API.
- **Option Y** — Introduce a backend narration worker that receives a job from
  `conversion/complete` and orchestrates TTS independently.

## Decision

**Option X** — pdf-processor orchestrates narration as the final pipeline stage.

Rationale:

- The processor already owns R2 credentials, the Redis job model, and the
  `pipeline_client` helper for internal backend calls.
- Adding a separate worker service increases deployment surface and inter-service
  messaging without proportional benefit at the current scale.
- Long-running TTS work is acceptable inside the existing `BackgroundTasks`
  runner because each processor instance handles one job at a time already, and
  the proxy queue gates concurrency.

## Consequences

- TTS provider credentials (`TTS_SERVICE_BASE_URL`, `DEFAULT_BASIC_VOICE_ID`)
  must be available to pdf-processor via environment variables.
- A new `pipeline_client` function (`generate_and_persist_narration`) calls the
  TTS service, uploads the stitched MP3 to R2, then PATCHes the backend book.
- If TTS fails, the book is still created (text extraction succeeded); the
  `narration_status` field on the book is set to `"failed"` via the PATCH
  endpoint, and the frontend shows an appropriate message.
