#!/usr/bin/env bash
# One-time bootstrap for a fresh Hostinger Ubuntu 24.04 VPS.
# Installs: Node.js 22, Python venv tooling, MongoDB 7, nginx, Claude Code.
# Run as root:  bash deploy/setup-vps.sh
set -euo pipefail

echo ">>> Updating apt and installing base packages..."
apt-get update -y
apt-get install -y curl gnupg ca-certificates git build-essential \
    python3 python3-venv python3-pip nginx ufw

echo ">>> Installing Node.js 22.x..."
if ! command -v node >/dev/null || [ "$(node -v | cut -dv -f2 | cut -d. -f1)" -lt 18 ]; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
    apt-get install -y nodejs
fi
node -v && npm -v

echo ">>> Installing MongoDB 7.0..."
if ! command -v mongod >/dev/null; then
    curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc \
        | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
    echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
        > /etc/apt/sources.list.d/mongodb-org-7.0.list
    apt-get update -y
    apt-get install -y mongodb-org
fi
systemctl enable --now mongod
systemctl status mongod --no-pager | head -5 || true

echo ">>> Installing Claude Code CLI globally..."
npm install -g @anthropic-ai/claude-code
claude --version || true

echo ">>> Configuring firewall (SSH + HTTP/HTTPS)..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo ""
echo ">>> Base setup complete."
echo ">>> Next: copy your env files, then run  bash deploy/deploy-app.sh"
echo ">>> To start Claude Code, run:  claude   (it will prompt you to log in via browser)"
