#!/usr/bin/env bash
# Build + (re)deploy the Nalanda ERP app on the VPS.
# Run from the repo root after setup-vps.sh and after creating the .env files.
#   bash deploy/deploy-app.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# --- Backend ---
echo ">>> Setting up backend (Python venv)..."
if [ ! -f backend/.env ]; then
    echo "ERROR: backend/.env is missing. Copy deploy/backend.env.example to backend/.env and fill it in." >&2
    exit 1
fi
python3 -m venv backend/.venv
# shellcheck disable=SC1091
source backend/.venv/bin/activate
pip install --upgrade pip
# emergentintegrations lives on a custom index; the extra-index covers it.
pip install -r backend/requirements.txt \
    --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
deactivate

# --- Frontend ---
echo ">>> Building frontend..."
if [ ! -f frontend/.env ]; then
    echo "ERROR: frontend/.env is missing. Copy deploy/frontend.env.example to frontend/.env and fill it in." >&2
    exit 1
fi
cd frontend
npm install
npm run build
cd "$REPO_DIR"

# --- systemd backend service ---
echo ">>> Installing systemd service for the backend..."
sed "s#__REPO_DIR__#${REPO_DIR}#g" deploy/nalanda-backend.service \
    | sudo tee /etc/systemd/system/nalanda-backend.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable nalanda-backend
sudo systemctl restart nalanda-backend

echo ""
echo ">>> App deployed."
echo ">>> Backend:  systemctl status nalanda-backend"
echo ">>> Frontend build is in frontend/build (served by nginx — see deploy/nginx.conf.example)."
