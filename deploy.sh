#!/usr/bin/env bash
# Nalanda ERP — one-shot deploy helper for a Docker-capable VPS.
# Usage:  ./deploy.sh            (build + start)
#         ./deploy.sh logs       (follow logs)
#         ./deploy.sh down        (stop)
set -euo pipefail
cd "$(dirname "$0")"

# Pick "docker compose" (v2) or fall back to "docker-compose" (v1).
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "ERROR: Docker Compose not found. Install Docker Engine + the compose plugin." >&2
  exit 1
fi

case "${1:-up}" in
  logs) exec $DC logs -f ;;
  down) exec $DC down ;;
  up)
    if [ ! -f .env ]; then
      cp .env.example .env
      # Auto-generate a JWT secret if the user hasn't set one.
      SECRET="$(openssl rand -hex 32 2>/dev/null || head -c32 /dev/urandom | xxd -p | tr -d '\n')"
      sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${SECRET}|" .env
      echo ">> Created .env with a generated JWT_SECRET."
      echo ">> Review .env (admin password, optional keys) then re-run: ./deploy.sh"
      exit 0
    fi
    echo ">> Building and starting Nalanda ERP ..."
    $DC up -d --build
    echo ">> Up. App: http://<your-server-ip>:$(grep -E '^HTTP_PORT=' .env | cut -d= -f2 || echo 80)"
    echo ">> Logs: ./deploy.sh logs"
    ;;
  *) echo "Usage: ./deploy.sh [up|logs|down]"; exit 1 ;;
esac
