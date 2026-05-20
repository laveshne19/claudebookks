"""Tiny SQLite persistence layer. No ORM — keeps the deploy dependency-free.

Stores the trade log, daily equity snapshots and a key/value state table
(so the dashboard survives restarts).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from typing import Any, Optional

from .models import Order

_SCHEMA = """
CREATE TABLE IF NOT EXISTS trades (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    qty         INTEGER NOT NULL,
    price       REAL NOT NULL,
    status      TEXT NOT NULL,
    order_id    TEXT,
    reason      TEXT,
    mode        TEXT NOT NULL,
    realized_pnl REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS equity (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    equity  REAL NOT NULL,
    cash    REAL NOT NULL,
    pnl     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS kv (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self._path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # --- trades ----------------------------------------------------------
    def record_trade(self, order: Order, mode: str, realized_pnl: float = 0.0) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO trades
                   (ts, symbol, side, qty, price, status, order_id, reason, mode, realized_pnl)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    order.ts,
                    order.symbol,
                    order.side.value,
                    order.qty,
                    order.price,
                    order.status.value,
                    order.order_id,
                    order.reason,
                    mode,
                    realized_pnl,
                ),
            )
            self._conn.commit()

    def recent_trades(self, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def realized_pnl_total(self) -> float:
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(realized_pnl),0) AS s FROM trades"
            ).fetchone()
        return float(row["s"])

    # --- equity curve ----------------------------------------------------
    def record_equity(self, ts: str, equity: float, cash: float, pnl: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO equity (ts, equity, cash, pnl) VALUES (?,?,?,?)",
                (ts, equity, cash, pnl),
            )
            self._conn.commit()

    def equity_curve(self, limit: int = 500) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, equity, cash, pnl FROM equity ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    # --- key/value -------------------------------------------------------
    def set_state(self, key: str, value: Any) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO kv (k, v) VALUES (?, ?) "
                "ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, json.dumps(value)),
            )
            self._conn.commit()

    def get_state(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT v FROM kv WHERE k=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["v"])
        except json.JSONDecodeError:
            return default

    def close(self) -> None:
        with self._lock:
            self._conn.close()
