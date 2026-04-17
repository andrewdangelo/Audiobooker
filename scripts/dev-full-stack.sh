#!/usr/bin/env bash
# Start MongoDB, Redis, Postgres, API proxy, and core Python microservices for local development.
# Usage (from repo root): bash scripts/dev-full-stack.sh
#
# Frontend (Vite) is not containerized here — run separately:
#   cd frontend && npm run dev
#
# AI service has no Dockerfile in this repo yet; start it manually if you need character/voice APIs.
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

exec docker compose --profile fullstack up --build "$@"
