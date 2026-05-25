# Single-voice conversion: state assessment and beta validation report

**Date:** 2026-05-11  
**Scope:** End-to-end single-voice conversion (PDF/EPUB upload → library → playback), credits purchase, store purchase with basic credits, account flows. Multi-voice is out of scope except where shared code affects single-voice.

**Evidence types used:**

- **Static:** repository source inspection (file paths cited).
- **Runtime:** local API proxy health probe returned unreachable (stack not running in assessment environment); browser E2E and screenshots are marked **pending** and should be executed on a fully configured staging stack.

---

## 1. Executive summary and beta recommendation

### Verdict: **No-go** for a public beta of “single-voice audiobook conversion” as a complete product

The stack implements **authentication**, **Stripe-backed credit purchases**, **store catalog and library fulfillment for single-book credit purchases**, and **PDF/EPUB upload with text extraction** into R2 plus a **library book row**. It does **not** yet implement a reliable path from extracted text to **generated, stored, attributable narration audio** tied to the book, nor a working **preview → confirm** flow exposed by the backend.

### Top five blockers (P0)

1. **No real TTS pipeline on the upload path:** `pdf-processor` completes with processed text and optional script; it does not call TTS batch synthesis or persist chapter/audio assets. Backend creates books with `chapters: []` and `audio_url: None` (see `microservices/backend/app/routers/internal.py`).
2. **Playback placeholder:** `GET .../audiobooks/{book_id}/audio` returns a fabricated `https://cloudflare/{book_id}.mp3` when `audio_url` is missing (`microservices/backend/app/routers/playback.py`), so “success” in the UI does not imply a real file.
3. **Preview and confirm APIs missing:** Frontend route `/preview/:previewId` and `AudiobookPreview.tsx` call `/backend/previews/...` and `/tts_infra/tts_processor/previews/...`. Backend has **no** `previews` router; TTS service exposes `/generate` and `/batch` only under `tts_processor`, **not** preview CRUD (`microservices/tts-infrastructure/app/routers/tts.py`). Users hitting preview will see **404** from a running stack.
4. **Cart checkout with credits does not fulfill library:** `checkout` with `paymentMethod === 'credits'` only calls `paymentService.payWithCredits` and returns; it never calls `storeService.purchase` (`frontend/src/store/slices/cartSlice.ts`). Single-book flow `purchaseBook` with credits does call `storeService.purchase` after pay-with-credits (`frontend/src/store/slices/storeSlice.ts`).
5. **Misleading progress UI:** On processor job `completed`, the client marks “Character Voice Assignment” and “TTS Conversion” as complete regardless of whether TTS ran (`frontend/src/store/slices/uploadJobsSlice.ts`).

Secondary P0/P1: `purchaseBook` with `useCredits: false` calls `storeService.purchase` only (no PaymentIntent). Premium cart/card paths likely need `premium-purchase` alignment (see defect table).

---

## 2. Environment and service graph (Phase A)

### 2.1 Canonical local full stack

From repository artifacts:

| Source | Command / notes |
|--------|------------------|
| Docker | `docker compose --profile fullstack up --build` from repo root (`docker-compose.yml` header comments). |
| Script | `bash scripts/dev-full-stack.sh` → wraps the same compose profile. |
| Frontend | **Not** in compose: `cd frontend && npm run dev` (script comment). |
| AI service | Script notes: **no Dockerfile**; start manually if voice APIs needed. |

### 2.2 Services in `fullstack` profile

| Service | Host port | Purpose |
|---------|-----------|---------|
| `mongodb` | 27017 | Auth, payment, backend, pdf-processor, TTS DBs |
| `redis` | 6379 | Proxy queues + pdf-processor jobs |
| `postgres` | 5433 | Present; primary app paths explored use Mongo |
| `api-proxy` | 8000 | Single entry: prefix `/api/v1/audiobooker_proxy` |
| `auth-service` | 8001 | JWT, accounts, credits |
| `backend` | 8002 | Books, store, library, playback, internal |
| `tts-infrastructure` | 8003 | TTS generate/batch |
| `pdf-processor` | 8004 | Upload, extract, notify backend |
| `payment-service` | 8005 | Stripe, pay-with-credits |

### 2.3 Frontend → proxy

`frontend/.env.example` sets `VITE_API_URL=http://localhost:8000/api/v1/audiobooker_proxy`, matching proxy `API_V1_PREFIX` in `api_proxy/app/core/config_settings.py`.

### 2.4 Critical env alignment for beta

- **R2:** PDF upload/processing requires real R2 credentials (`docker-compose.yml` notes placeholders only allow container start).
- **Stripe:** `STRIPE_*` in compose for `payment-service`.
- **Internal key:** `INTERNAL_SERVICE_KEY` in `pdf-processor` must match backend `INTERNAL_SERVICE_KEY` (`microservices/pdf-processor/app/core/config_settings.py`, `microservices/backend/.env.example`).
- **TTS providers:** `ELEVENLABS_API_KEY` / `OPENAI_API_KEY` in TTS settings gate providers (`tts.py`).

### 2.5 Documentation drift

Root `README.md` still describes `backend/` at repo root and Postgres-centric setup; the live architecture is **microservices + Mongo + api_proxy** (`docker-compose.yml`). Treat root README as **unreliable** for onboarding until updated.

---

## 3. API reconciliation (Phase B)

Proxy forwards by stripping the proxy prefix and appending `{path}` to each service base URL (`api_proxy/app/services/request_service.py`). TTS service mounts the main router at `{API_V1_PREFIX}/tts_processor` where `API_V1_PREFIX=/api/v1/tts` (`microservices/tts-infrastructure/main.py`), so full TTS paths are like `/api/v1/tts/tts_processor/generate`.

### 3.1 High-risk frontend ↔ backend mismatches

| Client usage | Expected downstream (after proxy) | Implemented? |
|--------------|-----------------------------------|----------------|
| `GET/POST /backend/previews/{id}...` | `BACKEND_SERVICE_URL/previews/...` | **No** — `microservices/backend/main.py` includes no previews router. |
| `PUT /tts_infra/tts_processor/previews/...` | `TTS_SERVICE_URL/tts_processor/previews/...` | **No** — no `previews` routes in `tts.py`. |
| `GET /backend/previews/{id}/status` | same | **No** |
| `POST /backend/previews/{id}/confirm` | same | **No** |
| `docs/07-api-reference.md` `POST /api/v1/conversion/start` | Backend conversion router | **No** — conversion handoff is `POST .../internal/conversion/complete` (service-to-service). |

### 3.2 Confirmed aligned paths (representative)

- `/auth/*` → auth-service (signup, login, refresh, accounts, `credits/consume-conversion`).
- `/payment/*` → payment-service (intents, webhooks, pay-with-credits).
- `/pdf_processor/*` → pdf-processor `.../pdf_processor/...`.
- `/backend/store/*`, `/backend/users/*`, `/backend/audiobooks/*` → backend routers under `API_V1_PREFIX=/api/v1`.

### 3.3 Credit lifecycle (static)

1. **Grant:** Stripe webhook / `complete-credit-purchase` in payment-service (see `paymentService.ts` and `payment-service` routers).
2. **Read:** `GET /auth/accounts/credits` and backend user credits endpoints used by `backendService` / `authService`.
3. **Consume for conversion:** `POST /auth/accounts/credits/consume-conversion` **before** upload (`accounts_mongo.py`, `FileUpload.tsx`). **No automatic refund** path was identified in this review if `process_pdf` fails after consumption (product risk E9).

---

## 4. Pipeline reports

### 4.1 Account pipeline

| Capability | Evidence | Gap |
|------------|----------|-----|
| Signup / login / JWT | `auth_mongo.py`, `Login.tsx`, `Signup.tsx`, proxy `/auth/*` | OK (static). |
| Email verification / onboarding wizard | `UserDocument.is_verified`; local signup default unverified but login not gated | Missing product flow. |
| Forgot password | `ForgotPassword.tsx` | Simulated / TODO; no Mongo reset router found in prior exploration. |
| Google OAuth | `authService` vs `POST /google/auth-url` response shape | Needs live verification (method/field mismatch risk). |

### 4.2 Upload pipeline

Flow: `FileUpload` → `consumeConversionCredit` → `uploadService.uploadPDF` → `processPDF` with metadata `{ credit_type }` → proxy → pdf-processor R2 + job + `process_pdf_task` → `notify_backend_conversion_complete`.

**Gap:** No `voice_id` or narrator profile in request body; “single narrator” is **copy only** in `CREDIT_OPTIONS` (`FileUpload.tsx` lines 43–49).

### 4.3 Conversion (text vs audio)

**Text extraction:** Implemented in `pdf_processor_service.py` (PDF/EPUB).

**Audio:** Not produced on this path. Internal book payload uses empty chapters and null `audio_url` (`internal.py`).

**TTS service:** `/generate`, `/batch` exist; processor uses health ping only for TTS stage (see plan / `pdf_processor_service.py`).

### 4.4 Purchase pipeline

| Flow | Behavior (static) | Risk |
|------|-------------------|------|
| `purchaseBook` + credits | `payWithCredits` then `storeService.purchase(..., 'credits')` | Coherent if payment service deducts correctly. |
| `purchaseBook` + card | **Only** `storeService.purchase(..., 'card')` | **No charge** — P0. |
| `purchasePremiumBook` | `POST /backend/store/premium-purchase` | Use for premium SKU; verify card path verifies PaymentIntent server-side (`payments.py` comments in exploration). |
| `cartSlice.checkout` + credits | `payWithCredits` only | **No library rows** — P0. |
| `cartSlice.checkout` + card | Loops `storeService.purchase(..., 'card')` | Basic fulfillment only; edition from cart not passed — premium mismatch risk. |

### 4.5 Usage pipeline

- **Library:** Books added after successful processor job (`pollProcessorJob` fetches book).
- **Listen:** Player depends on `get_audio_url`; placeholder URL if `audio_url` null — user may hit **404** or wrong asset.

---

## 5. E2E validation matrix (Phase C)

**Legend:** **S** = static code review result; **R** = requires running stack (not executed here).

| ID | Scenario | Result | Notes |
|----|----------|--------|------|
| E1 | Signup → login → settings → logout → login | **S: Likely pass** | Standard JWT path; verify CORS + proxy in R. |
| E2 | Forgot password | **S: Fail UX** | Non-API simulation in UI. |
| E3 | Buy basic credits (Stripe test) | **R: Pending** | Requires Stripe keys + payment-service. |
| E4 | Store book with basic credits only | **S: Partial** | `purchaseBook` credits path calls fulfillment; **R** to confirm balances and library row. |
| E5 | Cart → checkout with credits | **S: Fail** | No `storeService.purchase` after `payWithCredits` in `cartSlice.ts` (lines 181–198). |
| E6 | Cart/card premium vs basic | **S: Risk** | Card branch always `storeService.purchase(..., 'card')`; edition not applied — **R** to confirm `is_premium`. |
| E7 | PDF + basic credit → library → playback | **S: Partial fail** | Text/job may succeed; real audio absent; playback placeholder. |
| E8 | EPUB same | **S: Same as E7** | EPUB supported in processor validation. |
| E9 | Failure after credit consume | **S: Risk** | No refund path identified in `consume_conversion_credit` / upload error handling review. |
| E10 | `/preview/:previewId` | **S: Fail** | Backend + TTS preview routes absent. |

**Runtime follow-up:** Re-run E1–E10 on staging with HAR export, Mongo snapshots for `books` / `user_library` / `users`, and R2 object listing per job.

---

## 6. UX and usability (Phase D)

### 6.1 Cognitive walkthrough (first-time single-voice)

1. **Signup:** Lands on dashboard; no guided “how credits work” unless discovered in store/settings.
2. **Credits:** Purchase flows exist under `Purchase.tsx` / pricing; verify post-purchase balance refresh (Redux `fetchUserCredits`).
3. **Upload:** Clear file type/size messaging; **mismatch:** basic tier promises “suggested voice swap before finalizing” (`FileUpload.tsx`, `CREDIT_OPTIONS`) but on success the app navigates to `/library` (`navigate('/library')` in the same file) with no voice-swap step.
4. **Progress:** Users see “TTS Conversion” complete — **violates Nielsen #1 (visibility of status)** when the system did not synthesize audio.
5. **Outcome:** Book appears in library; play may fail or play placeholder — **violates Nielsen #4 (consistency)** and trust.

### 6.2 Heuristic highlights

| Heuristic | Finding |
|-----------|---------|
| Match system to real world | “Audiobook” implies audio; current path is closer to “text extraction + library card.” |
| Error prevention | Double-spend risk if user retries upload after transient failure (credit already consumed). |
| Recognition vs recall | Preview route exists in `App.tsx` but backend missing — broken deep links if marketing sends `/preview/...`. |

### 6.3 Accessibility (spot-check recommendation)

Run axe or Lighthouse on `/login`, `/signup`, `/checkout`, upload dialog, and audio player when stack is up; not executed in this pass.

---

## 7. Defect and backlog table

| ID | Sev | Area | Description | Suggested owner |
|----|-----|------|-------------|-----------------|
| D1 | P0 | Conversion | No TTS orchestration from `process_pdf_task` to persisted `audio_url` / chapters. | Backend + pdf-processor or new worker |
| D2 | P0 | API | Missing `/previews` on backend and TTS for all `AudiobookPreview` / `ttsService` preview calls. | Backend + TTS |
| D3 | P0 | Store | Cart credits checkout never calls `storeService.purchase`. | Frontend `cartSlice.ts` |
| D4 | P0 | Store | `purchaseBook` card path skips Stripe. | Frontend `storeSlice.ts` |
| D5 | P0 | Playback | Placeholder `audioUrl` when null. | `playback.py` — return 404 or disable play until real URL |
| D6 | P1 | UX | Upload progress stages misrepresent TTS/voice work. | Frontend `uploadJobsSlice.ts` + copy |
| D7 | P1 | Product | No voice selection on upload path despite copy. | Product + API contract |
| D8 | P1 | Payments | Premium cart + card may fulfill as basic; verify `edition` plumbing. | Frontend cart/checkout + backend |
| D9 | P1 | Credits | No refund if processing fails after consume. | Auth + processor error contract |
| D10 | P2 | Docs | Root README vs microservices architecture. | Docs |
| D11 | P2 | Docs | `docs/07-api-reference.md` conversion endpoints vs `internal/conversion/complete`. | Docs or implement |
| D12 | P2 | Proxy | Multipart queue uses `latin1` decode (`proxy_router.py`) — binary corruption risk if queue used. | api_proxy |

---

## 8. Beta launch checklist (engineering)

- [ ] Implement or remove preview UI; align `App.tsx` route with real APIs.
- [ ] Single canonical “full narration” job: chunk text → TTS → upload R2 → update book `audio_url` / chapters.
- [ ] Fix cart credits fulfillment; fix card `purchaseBook`; add server-side PaymentIntent verification for premium card.
- [ ] Replace playback placeholder with explicit “processing” / “not available” or signed URL to real object.
- [ ] Align upload progress labels with actual stages.
- [ ] Document and test env: R2, Stripe, internal keys, TTS keys.
- [ ] Regression suite for E1–E10 on CI or scheduled staging.

---

## 9. Out of scope (explicit)

- **Multi-voice casting:** Optional LLM script and `assign_voice_*` in `ai-service` are not wired into the upload pipeline; premium flag is mostly metadata today.
- **Performance/load testing** of proxy queues.

---

## 10. Appendix: key file index

| Concern | Path |
|---------|------|
| Proxy routes | `api_proxy/app/routers/proxy_router.py` |
| Forwarding | `api_proxy/app/services/request_service.py` |
| Auth credits consume | `microservices/auth-service/app/routers/accounts_mongo.py` |
| Internal book create | `microservices/backend/app/routers/internal.py` |
| Playback URL | `microservices/backend/app/routers/playback.py` |
| Upload UI | `frontend/src/components/upload/FileUpload.tsx` |
| Job stages UI | `frontend/src/store/slices/uploadJobsSlice.ts` |
| Cart checkout | `frontend/src/store/slices/cartSlice.ts` |
| Single-book purchase | `frontend/src/store/slices/storeSlice.ts` |
| Preview page | `frontend/src/pages/AudiobookPreview.tsx` |
| TTS HTTP surface | `microservices/tts-infrastructure/app/routers/tts.py` |
| Full stack compose | `docker-compose.yml` |
| Dev script | `scripts/dev-full-stack.sh` |

---

*End of report.*
