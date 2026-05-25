# API Reference

All requests go through the **api-proxy** at `http://localhost:8000`. The proxy
prefixes are mapped to microservices as follows:

| Proxy prefix | Microservice | Default port |
|-------------|-------------|-------------|
| `/auth/` | auth-service | 8001 |
| `/backend/` | backend | 8002 |
| `/tts_infra/` | tts-infrastructure | 8003 |
| `/pdf_processor/` | pdf-processor | 8004 |
| `/payment/` | payment-service | 8005 |

## Authentication

Most endpoints require a JWT `Authorization: Bearer <token>` header. Tokens are
issued by the auth-service on login/signup and refreshed via
`POST /auth/auth/refresh`.

Internal (service-to-service) endpoints require an
`X-Internal-Service-Key` header matching the shared `INTERNAL_SERVICE_KEY`
environment variable.

---

## Auth Service (`/auth/`)

### POST /auth/auth/signup
Create a new account. Returns access and refresh tokens.

### POST /auth/auth/login
Authenticate with email + password.

### POST /auth/auth/refresh
Exchange a refresh token for a new access token.

### GET /auth/accounts/credits
Get the current user's basic and premium credit balances.

### POST /auth/accounts/credits/consume-conversion
Deduct one basic or premium credit before starting a conversion.

### POST /auth/accounts/credits/refund-conversion (internal)
Refund one credit after a pipeline failure. Requires `X-Internal-Service-Key`.

---

## PDF Processor (`/pdf_processor/pdf_processor/`)

### POST /pdf_processor/pdf_processor/upload_new_pdf?user_id={id}
Upload a PDF or EPUB file (multipart/form-data). Returns an R2 key and
`pdf_path` for the next step.

### POST /pdf_processor/pdf_processor/process_pdf?user_id={id}
Start text extraction (and optional TTS narration) as a background job.

**Body:**
```json
{
  "r2_pdf_path": "uuid/pdf/file.pdf",
  "metadata": {
    "credit_type": "basic",
    "voice_id": "21m00Tcm4TlvDq8ikWAM"
  }
}
```

### GET /pdf_processor/pdf_processor/job/{job_id}?user_id={id}
Poll job status. Returns `status`, `progress` (0-100), `pipeline_stage`,
`audiobook_id` (on completion), and `error` (on failure).

---

## Backend (`/backend/`)

### GET /backend/audiobooks?user_id={id}
List all books in the user's library.

### GET /backend/audiobooks/{book_id}?user_id={id}
Get a single book's detail (includes `audio_url`, `narration_status`,
`chapters`).

### GET /backend/audiobooks/{book_id}/audio?user_id={id}
Get the streaming audio URL for a book. Returns `"status": "pending_audio"`
with `"audioUrl": null` when narration is not yet ready.

### POST /backend/store/purchase?user_id={id}
Add a store book to the user's library (idempotent).

### POST /backend/store/premium-purchase?user_id={id}
Purchase the premium (theatrical) edition. Supports `premium_credits` or `card`
payment methods. Card purchases are verified server-side via Stripe.

### Internal: POST /backend/internal/conversion/complete
Called by pdf-processor after extraction. Creates the book + library entry.

### Internal: PATCH /backend/internal/books/{book_id}/audio
Called by pdf-processor after TTS narration. Sets `audio_url`, `duration`,
`narration_status`.

---

## TTS Infrastructure (`/tts_infra/tts_processor/`)

### POST /tts_infra/tts_processor/generate
Generate TTS audio for a single text chunk.

### POST /tts_infra/tts_processor/batch
Generate TTS audio for multiple chunks at once. Used by the narration pipeline.

### GET /tts_infra/tts_processor/audio/{chunk_id}
Download the generated MP3 for a chunk.

### GET /tts_infra/tts_processor/voices/{provider}
List available voices for a provider (`elevenlabs` or `openai`).

### Audio stitching

- `POST /tts_infra/audio_stitching/stitch-and-save` — Stitch chunk audio files
  into a single MP3.
- `GET /tts_infra/audio_stitching/download/{job_id}` — Download stitched audio.
- `WS /tts_infra/audio_stitching/stream` — Stream stitched audio in real time.

---

## Payment Service (`/payment/`)

### GET /payment/config/publishable-key
Returns the Stripe publishable key for frontend initialization.

### POST /payment/create-payment-intent
Create a Stripe PaymentIntent (for Stripe Elements card form).

### POST /payment/complete-credit-purchase
Grant credits after a Stripe PaymentIntent succeeds (idempotent).

### POST /payment/pay-with-credits
Deduct credits for a purchase (books or cart).

### POST /payment/create-checkout-session
Create a Stripe hosted checkout session.

---

## Proxy health and queues

### GET /health
Aggregated health of all services, Redis, and queue depths.

### GET /queue/{queue_id}
Check the status of a queued (rate-limited) request.

---

## Status codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 202 | Accepted (queued) |
| 400 | Bad request |
| 402 | Payment required / insufficient credits |
| 403 | Forbidden (bad internal key or ownership) |
| 404 | Not found |
| 502 | Upstream service error |

## CORS

Allowed origins (configurable via `CORS_ORIGINS`):
- `http://localhost:5173`
- `http://localhost:3000`
