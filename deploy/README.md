# Hostinger VPS setup & deployment

This guide installs **Claude Code** on your Ubuntu 24.04 VPS and deploys the
Nalanda ERP app (FastAPI + MongoDB backend, React frontend).

## 0. Connect to the VPS

```bash
ssh root@147.93.96.18
```

(Optional but recommended) create a non-root user and use it instead:

```bash
adduser lavesh && usermod -aG sudo lavesh && su - lavesh
```

## 1. Get the code

```bash
git clone https://github.com/laveshne19/claudebookks.git
cd claudebookks
git checkout claude/hostinger-vps-setup-NAoY3
```

## 2. One-time system bootstrap

Installs Node.js 22, Python, MongoDB 7, nginx, the firewall, **and Claude Code**:

```bash
sudo bash deploy/setup-vps.sh
```

## 3. Start Claude Code

```bash
claude
```

On first run it opens a browser login link — sign in with your Claude
subscription account (`laveshne19@gmail.com`). After that, `claude` works in
any SSH session on this server.

## 4. Configure environment

```bash
cp deploy/backend.env.example  backend/.env
cp deploy/frontend.env.example frontend/.env
nano backend/.env      # set JWT_SECRET, ADMIN_*, EMERGENT_LLM_KEY, Zoho creds
nano frontend/.env     # set REACT_APP_BACKEND_URL to your domain or http://147.93.96.18
```

## 5. Deploy the app

Builds the frontend, installs backend deps in a venv, and registers the
backend as a systemd service:

```bash
bash deploy/deploy-app.sh
```

## 6. Wire up nginx

```bash
REPO_DIR=$(pwd)
sed "s#__REPO_DIR__#${REPO_DIR}#g; s#YOUR_DOMAIN_OR_IP#147.93.96.18#g" \
    deploy/nginx.conf.example | sudo tee /etc/nginx/sites-available/nalanda
sudo ln -sf /etc/nginx/sites-available/nalanda /etc/nginx/sites-enabled/nalanda
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

Visit `http://147.93.96.18`. The frontend is served statically; `/api` is
proxied to the backend on port 8001.

### HTTPS (after pointing a domain at the VPS)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx
```

## Operations

| Action | Command |
| --- | --- |
| Backend logs | `journalctl -u nalanda-backend -f` |
| Restart backend | `sudo systemctl restart nalanda-backend` |
| Rebuild after `git pull` | `bash deploy/deploy-app.sh` |
| MongoDB status | `systemctl status mongod` |

## Notes

- `emergentintegrations` is pulled from a custom pip index (handled by
  `deploy-app.sh`).
- `.env` files are git-ignored — keep secrets off GitHub.
- The mobile app (Capacitor) wraps the same frontend; build it separately on a
  machine with the Android/iOS SDKs.
