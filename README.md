# Audiobooker

A modern web application that converts PDF and EPUB documents into audiobooks
using AI-powered text-to-speech. Upload a book, choose a voice, and get a
narrated MP3 in your library.

## Architecture

Audiobooker is a microservices system fronted by a single API proxy.

```
frontend (React/Vite)
     │
     ▼
api-proxy :8000  ── rate-limits, queues, forwards ──┐
     │                                               │
     ├── auth-service      :8001  (JWT, credits)     │
     ├── backend           :8002  (library, books)   │
     ├── tts-infrastructure:8003  (ElevenLabs/OpenAI)│
     ├── pdf-processor     :8004  (extract + narrate)│
     └── payment-service   :8005  (Stripe, credits)  │
                                                     │
     MongoDB 27017  ◄────────────────────────────────┘
     Redis   6379
     Postgres 5433 (legacy, not actively used)
```

### Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, shadcn/ui, Redux Toolkit |
| Backend services | Python 3.11+, FastAPI, Pydantic v2 |
| Databases | MongoDB 7 (primary), Redis 7 (queues/cache), PostgreSQL 15 (legacy) |
| Object storage | Cloudflare R2 |
| Payments | Stripe (PaymentIntents, checkout sessions, webhooks) |
| TTS providers | ElevenLabs, OpenAI TTS |

## Quick start

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- Docker and Docker Compose

### 1. Start infrastructure

```bash
docker compose up -d          # MongoDB, Redis, Postgres
```

### 2. Start the full API stack (optional)

```bash
docker compose --profile fullstack up --build
```

Or run services individually — each microservice has its own `.env` file and
`requirements.txt` under `microservices/<name>/`.

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

### Environment variables

Each microservice reads from a `.env` at its own root. Key variables:

| Variable | Service | Purpose |
|----------|---------|---------|
| `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` | pdf-processor | Cloudflare R2 credentials |
| `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY` | payment-service, backend | Stripe keys |
| `ELEVENLABS_API_KEY` | tts-infrastructure | ElevenLabs API key |
| `INTERNAL_SERVICE_KEY` | all services | Shared secret for service-to-service calls |
| `DEFAULT_BASIC_VOICE_ID` | pdf-processor, backend | Default ElevenLabs voice for basic narration |

## Project structure

```
audiobooker/
├── frontend/                    # React SPA
├── api_proxy/                   # FastAPI proxy + Redis queue workers
├── microservices/
│   ├── auth-service/            # Signup, login, JWT, credits
│   ├── backend/                 # Library, books, playback, internal APIs
│   ├── payment-service/         # Stripe integration, credit packs
│   ├── pdf-processor/           # PDF/EPUB extraction + TTS narration
│   └── tts-infrastructure/      # TTS generation + audio stitching
├── docs/                        # Architecture docs, ADRs, assessment
├── docker-compose.yml
└── README.md
```

## Key user flows

1. **Sign up / login** — auth-service issues JWT access + refresh tokens.
2. **Buy credits** — payment-service creates a Stripe PaymentIntent; credits
   are granted on confirmation.
3. **Upload a PDF/EPUB** — frontend consumes one credit, uploads to
   pdf-processor, which extracts text, calls TTS `/batch`, uploads audio to R2,
   and patches the backend book record.
4. **Listen** — backend serves the R2 audio URL; the frontend player streams it.
5. **Store purchase** — single-book or cart checkout via credits or card.

## Documentation

- [Architecture overview](./docs/)
- [ADR-001: TTS orchestrator](./docs/adr/001-tts-narration-orchestrator.md)
- [Beta assessment report](./docs/BETA_SINGLE_VOICE_ASSESSMENT_REPORT.md)
- [API reference](./docs/07-api-reference.md) (being updated)

## License

MIT
