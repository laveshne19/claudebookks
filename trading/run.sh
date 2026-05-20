#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# Create venv on first run
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  ./.venv/bin/pip install --upgrade pip
  ./.venv/bin/pip install -r requirements.txt
fi

# Copy env template on first run
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from template — edit it before going live."
fi

PORT="${PORT:-8080}"
exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
