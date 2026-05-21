# NE Kite Autotrader

A production intraday trading bot for Indian equities (NSE, MIS) via the
Zerodha **KiteConnect** API. It replicates a 5-indicator weighted-scoring
strategy with an optional Claude AI overlay, runs an in-process scheduler
(no 6-minute timeout), and ships a localhost-only FastAPI dashboard.

> **REAL MONEY.** The bot is **paper-mode by default**. Real orders are placed
> only when `LIVE_MODE=true` in `.env`. Read the safety section before going live.

## Safety model (non-negotiable)

| Rule | Enforced by |
|------|-------------|
| Paper mode locked ON unless `LIVE_MODE=true` | `config.py`, `trader._effective_paper()` |
| Daily loss > 5% of capital → kill switch (stops for the day) | `risk_manager.check_daily_loss` |
| Max risk per trade 2% (hard-capped) | `risk_manager.calculate_position_size` |
| Confidence threshold ≥ 60% (never below 50%) | `config.py` validation, `strategy.evaluate` |
| Square-off all positions at 15:15 IST | `main.py` cron job, `trader.square_off_all` |
| No trades outside 09:15–15:30 IST, weekends, NSE holidays | `market.py` |
| No new entries after 15:00 IST | `market.can_open_new_position` |
| ≥ 5 open positions → no new trades | `risk_manager.can_trade` |
| 3 consecutive losses → halve size | `risk_manager.size_multiplier` |
| No secrets in code (`.env`, gitignored) | `.gitignore`, `.env.example` |
| Dashboard cannot flip to LIVE (only force-paper) | `dashboard.py` |

## Architecture

```
app/
  config.py        # .env loader + validation, 30-stock watchlist
  market.py        # IST market-hours / holiday calendar
  database.py      # sqlite3 schema + helpers (no ORM)
  kite_client.py   # defensive KiteConnect wrapper (pure broker adapter)
  kite_login.py    # CLI daily token generation
  indicators.py    # EMA, RSI, MACD, Supertrend, ATR, momentum (pure pandas)
  strategy.py      # weighted scoring -> BUY/SELL/HOLD
  risk_manager.py  # position sizing, stops, kill switch
  trader.py        # scan loop + (paper/live) execution
  claude_client.py # optional AI second-opinion overlay
  dashboard.py     # FastAPI + Jinja2 (basic auth, localhost)
  main.py          # APScheduler + uvicorn, graceful shutdown
scripts/
  import_trades.py # migrate historical trades from CSV/Excel
tests/             # pytest: indicators, strategy, risk manager
```

### Strategy scoring (weights sum to 100)

| Indicator | Weight | BUY when | SELL when |
|-----------|--------|----------|-----------|
| EMA 9 vs 21 | 20 | EMA9 > EMA21 | EMA9 < EMA21 |
| RSI(14) | 20 | < 30 | > 70 |
| MACD(12,26,9) | 20 | line > signal and > 0 | line < signal and < 0 |
| Supertrend(10,3) | 25 | price > line | price < line |
| Momentum(10) | 15 | close > close[-10] | close < close[-10] |

`buy_score`/`sell_score` are the summed weights of agreeing indicators. A trade
is considered only when the winning score ≥ `MIN_CONFIDENCE` (default 60) and
beats the other side. The Claude overlay can then veto with `HOLD`; Claude API
errors never block a rules-based trade.

## Setup

```bash
cd ne-trader
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in your values
python -m app.database init   # create data/trader.db
python -m app.kite_login      # generate today's access token
python -m app.main            # start (paper mode)
```

Access the dashboard via SSH tunnel (it binds to 127.0.0.1):

```bash
ssh -L 8000:localhost:8000 ubuntu@your-vps
# then open http://localhost:8000  (HTTP basic auth from .env)
```

## Daily token refresh

Kite tokens expire ~06:00 IST. Refresh either way:
- CLI: `python -m app.kite_login`
- Dashboard: **Token** page (`/auth/refresh`)

## Migrating historical trades

```bash
python scripts/import_trades.py path/to/export.csv --dry-run   # preview
python scripts/import_trades.py path/to/export.csv             # import
```
Headers are matched flexibly (`side`/`action`, `qty`/`quantity`,
`buy_price`/`entry`, etc.). Rows import as CLOSED real-money history.

## Going live (deliberate, manual)

1. Run ≥ 1 full day in paper mode; verify scans, decisions, dashboard.
2. Set `LIVE_MODE=true` in `.env`.
3. Restart the service. There is no auto-flip and no UI path to live.

## Run as a service

Edit `ne-trader.service` (User, paths), then:

```bash
sudo cp ne-trader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ne-trader
sudo journalctl -u ne-trader -f
```

## Testing

```bash
pytest tests/        # indicator math, strategy scoring, risk/kill-switch
```

## Logs

Rotating file handler at `logs/trader.log` (5 MB × 5 backups). Tail the last
100 lines from the dashboard `/logs` page.

## Notes / non-goals (v1)

No Selenium login, no Telegram (deferred), no WebSocket streaming (5-min
polling), no Docker, no Celery/Redis, no React build, no SQLAlchemy.
