"""
Thread-safe shared state for the trading signal dashboard.

The simulator writes to DashboardState; the Flask dashboard reads from it.
All mutations go through methods that hold a threading.Lock so the SSE
stream never sees a half-written snapshot.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from demo.config import LOG_RETENTION, TRADE_LOG_FILE


@dataclass
class DashboardState:
    """Central state object shared between the simulator and the dashboard."""

    # ---- raw storage (never touch directly -- use the methods) -----------
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    account_summary: dict = field(default_factory=lambda: {
        "starting_capital": 1000.00,
        "current_equity": 1000.00,
        "total_pnl": 0.00,
        "total_pnl_pct": 0.00,
        "available_cash": 1000.00,
        "unsettled_funds": 0.00,
        "day_trades_remaining": 3,
        "market_open": False,
        "market_status": "Closed",
        "next_event": "",            # e.g. "Opens in 2h 14m"
    })

    active_signals: list[dict] = field(default_factory=list)   # max 50
    open_positions: list[dict] = field(default_factory=list)
    trade_history: list[dict] = field(default_factory=list)
    equity_curve: list[tuple[str, float]] = field(default_factory=list)
    system_log: list[dict] = field(default_factory=list)       # max 200

    # -- version counter so the SSE loop can detect changes quickly --------
    _version: int = 0

    # ---- public helpers --------------------------------------------------
    @property
    def version(self) -> int:
        return self._version

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-safe deep copy of the full state."""
        with self._lock:
            return {
                "account_summary": dict(self.account_summary),
                "active_signals": list(self.active_signals),
                "open_positions": list(self.open_positions),
                "trade_history": list(self.trade_history),
                "equity_curve": list(self.equity_curve),
                "system_log": list(self.system_log),
                "version": self._version,
            }

    # ---- mutators --------------------------------------------------------
    def update_account(self, **kwargs: Any) -> None:
        with self._lock:
            self.account_summary.update(kwargs)
            self._version += 1

    def add_signal(self, signal: dict) -> None:
        with self._lock:
            signal.setdefault("timestamp", time.strftime("%H:%M:%S"))
            self.active_signals.insert(0, signal)
            if len(self.active_signals) > 50:
                self.active_signals = self.active_signals[:50]
            self._version += 1

    def update_positions(self, positions: list[dict]) -> None:
        with self._lock:
            self.open_positions = list(positions)
            self._version += 1

    def add_trade(self, trade: dict) -> None:
        with self._lock:
            self.trade_history.append(trade)
            self._version += 1

    def add_equity_point(self, timestamp: str, value: float) -> None:
        with self._lock:
            self.equity_curve.append((timestamp, value))
            self._version += 1

    def add_log(self, message: str, level: str = "INFO") -> None:
        with self._lock:
            entry = {
                "timestamp": time.strftime("%H:%M:%S"),
                "level": level,
                "message": message,
            }
            self.system_log.insert(0, entry)
            if len(self.system_log) > LOG_RETENTION:
                self.system_log = self.system_log[:LOG_RETENTION]
            self._version += 1

    def log_trade_to_file(self, trade_data: dict) -> None:
        """Append detailed trade record to JSONL file for future optimization."""
        trade_data["_logged_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(TRADE_LOG_FILE, "a") as f:
                f.write(json.dumps(trade_data, default=str) + "\n")
        except Exception:
            pass  # never crash on logging
