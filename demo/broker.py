"""Broker abstraction layer for production trading.

This module defines the interface that any broker implementation must follow.
The SimulatedAccount in simulator.py already implements this interface.
When ready to go live, implement the same interface with real broker APIs.

Supported brokers (planned):
  - E*Trade (Morgan Stanley) — OAuth 1.0a REST API
  - Alpaca — REST + WebSocket API (easiest for algo trading)
  - Interactive Brokers — TWS/Gateway API

Usage:
    # Simulation (current)
    from demo.simulator import SimulatedAccount
    account = SimulatedAccount(starting_cash=1000.0)

    # Production (future)
    from demo.broker import ETradeAccount
    account = ETradeAccount(api_key="...", secret="...", account_id="...")

    # Both implement the same interface:
    result = account.buy("AAPL", price=192.0, qty=1)
    result = account.sell("AAPL", price=195.0)
    equity = account.equity
    cash = account.available_cash
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BrokerAccount(ABC):
    """Abstract base class for broker account implementations.

    All trading operations go through this interface. The simulation
    engine and dashboard don't care whether orders are simulated or real —
    they just call these methods.
    """

    @property
    @abstractmethod
    def equity(self) -> float:
        """Total account value: cash + positions market value."""
        ...

    @property
    @abstractmethod
    def available_cash(self) -> float:
        """Cash available for new trades (excludes unsettled funds)."""
        ...

    @property
    @abstractmethod
    def unsettled_funds(self) -> float:
        """Funds locked in T+1 settlement."""
        ...

    @property
    @abstractmethod
    def day_trades_remaining(self) -> int:
        """Number of day trades left in the rolling 5-day window.
        Returns 999 if account is above PDT threshold ($25K)."""
        ...

    @property
    @abstractmethod
    def positions(self) -> dict[str, dict]:
        """Current open positions: {ticker: {qty, entry_price, current_price, ...}}."""
        ...

    @abstractmethod
    def can_buy(self, price: float, qty: int) -> tuple[bool, str]:
        """Check if a buy order can be placed. Returns (allowed, reason)."""
        ...

    @abstractmethod
    def can_day_trade(self) -> tuple[bool, str]:
        """Check PDT compliance. Returns (allowed, reason)."""
        ...

    @abstractmethod
    def compute_fees(self, price: float, qty: int, is_sell: bool) -> dict:
        """Compute fee breakdown for a trade.

        Returns dict with keys: total, commission, sec_fee, finra_taf, finra_cat.
        """
        ...

    @abstractmethod
    def buy(self, ticker: str, price: float, qty: int) -> dict:
        """Execute a buy order.

        Returns dict with: fill_price, slippage, fees, fee_breakdown, total_cost.
        """
        ...

    @abstractmethod
    def sell(self, ticker: str, price: float) -> dict | None:
        """Execute a sell order. Returns trade result dict or None if no position."""
        ...

    @abstractmethod
    def max_shares(self, price: float) -> int:
        """Maximum shares that can be purchased at the given price."""
        ...

    @abstractmethod
    def record_equity(self) -> None:
        """Record current equity for equity curve tracking."""
        ...


# ---------------------------------------------------------------------------
# Placeholder for future E*Trade implementation
# ---------------------------------------------------------------------------

class ETradeAccount(BrokerAccount):
    """E*Trade broker implementation (placeholder for production).

    To implement:
    1. Get API credentials from https://developer.etrade.com
    2. Implement OAuth 1.0a flow for authentication
    3. Use E*Trade REST API for order placement
    4. Map API responses to the BrokerAccount interface

    E*Trade API endpoints:
      - GET /v1/accounts/list — list accounts
      - GET /v1/accounts/{accountIdKey}/balance — account balance
      - GET /v1/accounts/{accountIdKey}/portfolio — positions
      - POST /v1/accounts/{accountIdKey}/orders/place — place order
      - GET /v1/market/quote/{symbols} — real-time quotes

    Fee structure (already coded in config.py):
      - $0 commission on online equity trades
      - SEC fee: $27.80 per million of sell proceeds
      - FINRA TAF: $0.000166 per share sold (max $8.30)
      - FINRA CAT: $0.000048 per covered transaction
      - Options: $0.65/contract ($0.50 for active traders)
    """

    def __init__(
        self,
        consumer_key: str = "",
        consumer_secret: str = "",
        account_id: str = "",
        sandbox: bool = True,
    ) -> None:
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._account_id = account_id
        self._sandbox = sandbox
        raise NotImplementedError(
            "E*Trade live trading is not yet implemented. "
            "Use SimulatedAccount for testing, or implement the "
            "E*Trade OAuth flow and REST API calls."
        )

    # All abstract methods would be implemented here, calling E*Trade REST API
    # For now, this class serves as documentation of what needs to be built.

    @property
    def equity(self) -> float:
        raise NotImplementedError

    @property
    def available_cash(self) -> float:
        raise NotImplementedError

    @property
    def unsettled_funds(self) -> float:
        raise NotImplementedError

    @property
    def day_trades_remaining(self) -> int:
        raise NotImplementedError

    @property
    def positions(self) -> dict[str, dict]:
        raise NotImplementedError

    def can_buy(self, price: float, qty: int) -> tuple[bool, str]:
        raise NotImplementedError

    def can_day_trade(self) -> tuple[bool, str]:
        raise NotImplementedError

    def compute_fees(self, price: float, qty: int, is_sell: bool) -> dict:
        raise NotImplementedError

    def buy(self, ticker: str, price: float, qty: int) -> dict:
        raise NotImplementedError

    def sell(self, ticker: str, price: float) -> dict | None:
        raise NotImplementedError

    def max_shares(self, price: float) -> int:
        raise NotImplementedError

    def record_equity(self) -> None:
        raise NotImplementedError
