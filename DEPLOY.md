# Deploying Nalanda ERP on a VPS

This app has three parts that run together:

- **MongoDB** — database
- **backend** — FastAPI API (`/api/*`), Python 3.11
- **frontend** — React 19 app, built to static files and served by nginx, which
  also reverse-proxies `/api` to the backend (so everything is one origin — no
  CORS headaches).

Everything is wired up with Docker Compose. The app runs **fully without any
API keys**; the Emergent LLM key and Zoho credentials are optional and only
enable live AI insights / Zoho Books sync.

---

## 1. Prerequisites on the VPS

- A Linux VPS (Ubuntu 22.04+ recommended), 2 GB RAM minimum.
- Docker Engine + Compose plugin:

  ```bash
  curl -fsSL https://get.docker.com | sh
  ```

- Ports: open **80** (and **443** if you add TLS) in the firewall / security group.

## 2. Get the code

```bash
git clone <your-repo-url> nalanda-erp
cd nalanda-erp
git checkout claude/nalanda-erp-setup-yictzd
```

## 3. Configure & launch

The helper script creates `.env` (with an auto-generated `JWT_SECRET`) on first
run, then builds and starts everything:

```bash
chmod +x deploy.sh
./deploy.sh          # 1st run: writes .env, then asks you to review it
nano .env            # set ADMIN_PASSWORD; optionally add EMERGENT_LLM_KEY / Zoho
./deploy.sh          # 2nd run: builds images and starts the stack
```

Or do it manually:

```bash
cp .env.example .env
# set JWT_SECRET (openssl rand -hex 32) and ADMIN_PASSWORD
docker compose up -d --build
```

## 4. Verify

```bash
curl http://localhost/api/health        # -> {"status":"ok", ...}
./deploy.sh logs                          # follow logs
```

Open `http://<your-server-ip>/` and log in with the seeded super-admin
(`ADMIN_EMAIL` / `ADMIN_PASSWORD`). On first boot the backend seeds demo data
(users, ~30 customers, invoices, schemes, targets).

Other seeded logins (password as in `memory/PRD.md`): `manager@nalanda.com`,
`sales1@nalanda.com`, `accounts@nalanda.com`.

## 5. Domain + HTTPS (recommended)

Point an A record at the VPS, then put a TLS-terminating proxy in front. Easiest
is Caddy:

```bash
# /etc/caddy/Caddyfile
erp.yourdomain.com {
    reverse_proxy localhost:80
}
```

(Or set `HTTP_PORT=8080` in `.env` and have nginx/Caddy on 443 proxy to it.)

---

## Updating

```bash
git pull
docker compose up -d --build
```

## Common operations

| Task                | Command                                             |
|---------------------|-----------------------------------------------------|
| Logs                | `./deploy.sh logs`                                  |
| Stop                | `./deploy.sh down`                                  |
| Restart backend     | `docker compose restart backend`                    |
| Mongo shell         | `docker compose exec mongo mongosh nalanda_erp`     |
| Backend tests       | `docker compose exec backend pytest`                |

## Notes & troubleshooting

- **Data persistence** — Mongo data lives in the `mongo_data` Docker volume; it
  survives restarts and rebuilds. `docker compose down -v` wipes it.
- **AI insights** without `EMERGENT_LLM_KEY` use deterministic fallbacks (the
  `emergentintegrations` package is Emergent-only and is treated as optional at
  both build and run time).
- **Split domains** — to serve the API on a separate host, set
  `REACT_APP_BACKEND_URL=https://api.yourdomain.com` before building the
  frontend; otherwise leave it empty for the single-domain setup above.
- **Frontend build fails on Node** — the image pins `node:20-alpine`, which is
  known-good for `react-scripts` 5 / CRACO.
