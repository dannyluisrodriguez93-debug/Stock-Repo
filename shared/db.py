"""SQLite persistence for signals, trades, and alerts."""

import os
from pathlib import Path

import aiosqlite

from shared.logging import get_logger

log = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    tickers TEXT NOT NULL,
    direction TEXT NOT NULL,
    catalyst_type TEXT NOT NULL,
    magnitude INTEGER NOT NULL,
    confidence REAL NOT NULL,
    flag_level TEXT NOT NULL,
    headline TEXT,
    source TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER REFERENCES signals(id),
    ticker TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_price REAL,
    target_price REAL,
    stop_loss REAL,
    exit_price REAL,
    exit_trigger TEXT,
    quantity INTEGER,
    pnl REAL,
    status TEXT DEFAULT 'pending',
    opened_at TEXT,
    closed_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER REFERENCES trades(id),
    channel TEXT NOT NULL,
    message TEXT,
    approved INTEGER,
    responded_at TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        os.makedirs(Path(self.db_path).parent, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(_SCHEMA)
        await self._db.commit()
        log.info("database_connected", path=self.db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def insert_signal(self, **kwargs) -> int:
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        sql = f"INSERT INTO signals ({cols}) VALUES ({placeholders})"
        cursor = await self._db.execute(sql, list(kwargs.values()))
        await self._db.commit()
        return cursor.lastrowid

    async def insert_trade(self, **kwargs) -> int:
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        sql = f"INSERT INTO trades ({cols}) VALUES ({placeholders})"
        cursor = await self._db.execute(sql, list(kwargs.values()))
        await self._db.commit()
        return cursor.lastrowid

    async def update_trade(self, trade_id: int, **kwargs) -> None:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        sql = f"UPDATE trades SET {sets} WHERE id = ?"
        await self._db.execute(sql, [*kwargs.values(), trade_id])
        await self._db.commit()

    async def insert_alert(self, **kwargs) -> int:
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join(["?"] * len(kwargs))
        sql = f"INSERT INTO alerts ({cols}) VALUES ({placeholders})"
        cursor = await self._db.execute(sql, list(kwargs.values()))
        await self._db.commit()
        return cursor.lastrowid
