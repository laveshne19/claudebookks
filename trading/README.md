# Auto-Trader — NSE (Indian market) automated trading

A self-contained automated trading system: a deterministic strategy engine
trades through a broker (paper or Dhan live), hard risk guardrails sit between
every signal and every order, Claude provides plain-English analysis on the
dashboard, and everything is logged.

> **This is not financial advice and does not guarantee profit.** Automated
> trading is risky and most retail strategies lose money. Run in `paper` mode
> until you have proven the strategy. See "Going live" and "Multi-user / SEBI"
> below before risking real money.

## What's inside

```
trading/
  app/
    config.py            # all settings via env / .env
    models.py            # Order / Position / Signal / Quote
    db.py                # SQLite trade log, equity curve, state
    brokers/
      base.py            # BrokerAdapter interface
      paper.py           # simulated broker (default, safe)
      dhan.py            # Dhan live adapter (real money)
    market/data.py       # Dhan live LTP + synthetic fallback feed
    strategy/            # SMA-crossover + RSI filter, pluggable
    engine/
      risk.py            # guardrails: caps, daily loss limit, stop-loss, kill switch
      trader.py          # the decision loop (signal -> risk -> order -> log)
    ai/claude.py         # Claude commentary (daily summary, risk, Q&A)
    main.py              # FastAPI REST + WebSocket + dashboard
    static/              # dashboard (no build step)
  tests/                 # 21 unit tests (broker, risk, strategy, engine)
```

## How trading decisions are made (read this)

Claude does **not** place trades. A deterministic strategy (`sma_crossover`)
reads live prices and emits BUY/SELL signals. Every signal passes through the
`RiskManager`, which sizes the position and can veto it. Claude's role is
**analysis only** — it reads the live state and explains, in plain English, what
the bot did and what the risks are. This separation is deliberate: LLMs are too
slow, too costly, and too prone to error to be the live order-routing brain.

## Run it (paper mode, zero risk)

```bash
cd trading
./run.sh              # creates .venv, installs deps, copies .env, starts server
# open http://localhost:8080
```

Or manually:

```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
cp .env.example .env
./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080
```

Paper mode trades on **real (≈15-min delayed) NSE prices** via Yahoo Finance —
no API key, no broker account needed (`PAPER_DATA_SOURCE=live`, the default). If
the host can't reach Yahoo, it automatically falls back to a **synthetic** price
feed so the engine, dashboard, and trade log still work offline. Set
`PAPER_DATA_SOURCE=synthetic` to force the offline feed for demos.

Use the dashboard's **Start**, **Step once**, and **PANIC** buttons; ask Claude
for a daily summary (needs `ANTHROPIC_API_KEY`).

> Note: paper mode is the right way to "run it just for yourself" first — real
> prices, simulated fills, zero financial risk. Let it run for a few sessions
> and review the trade log before considering live capital.

## Configuration

All settings live in `.env` (see `.env.example`). Key guardrails:

| Setting | Meaning | Default |
|---|---|---|
| `TRADING_MODE` | `paper` (safe) or `live` (real money) | `paper` |
| `MAX_TRADE_VALUE` | max ₹ per trade | 5000 |
| `MAX_OPEN_POSITIONS` | concurrent positions | 3 |
| `DAILY_LOSS_LIMIT` | bot halts for the day at this loss | 2000 |
| `STOP_LOSS_PCT` / `TAKE_PROFIT_PCT` | per-position exits | 1.5% / 3% |
| `SYMBOLS` | NSE tickers to trade | RELIANCE,TCS,INFY,HDFCBANK,SBIN |

## Going live with Dhan (real money — small capital)

1. Open a Dhan account and generate API credentials at
   web.dhan.co → Profile → DhanHQ Trading APIs.
2. Set in `.env`: `TRADING_MODE=live`, `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`.
3. Set `SECURITY_MAP` — Dhan identifies instruments by numeric `security_id`,
   not ticker. Map each symbol, e.g.
   `SECURITY_MAP={"RELIANCE":"2885","TCS":"11536","INFY":"1594"}`.
   (Download the official instrument master from Dhan to get correct IDs.)
4. Keep `MAX_TRADE_VALUE` and `DAILY_LOSS_LIMIT` tiny for the first weeks.

Safety: if `TRADING_MODE=live` but credentials/security map are missing, the
system automatically falls back to paper — it will never silently route real
orders without being fully configured. The **PANIC** button flattens everything
and engages the kill switch.

## Deploy on your VPS + domain

```bash
# on the VPS
git clone <repo> && cd <repo>/trading
cp .env.example .env && nano .env        # fill in keys, keep paper to start
./run.sh                                  # or use a systemd unit / pm2
```

Put Nginx in front for your domain + HTTPS (Let's Encrypt) and reverse-proxy to
`127.0.0.1:8080` (proxy the `/ws` WebSocket too). Run `uvicorn` under `systemd`
so it restarts on reboot. **Add authentication before exposing the dashboard
publicly** — v1 has no login (it's built for single-user / localhost).

## Roadmap to multi-user — and the SEBI reality

The broker layer is an interface, so multi-user (each user connects their own
Dhan/Kite account) is an architectural extension, not a rewrite. **But** running
a public service that auto-trades other people's accounts in India has real
regulatory weight: SEBI's algo-trading framework requires broker-approved/tagged
algos, and offering trade decisions to others can require SEBI Research
Analyst / Investment Adviser registration. Treat multi-user as a legal project,
not just a coding one. For your own account, none of that applies.

## Tests

```bash
./.venv/bin/python -m pytest -q     # 21 tests: broker, risk, strategy, engine
```
