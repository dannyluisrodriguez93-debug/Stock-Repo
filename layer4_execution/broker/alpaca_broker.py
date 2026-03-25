"""Alpaca broker adapter."""

import asyncio
from datetime import datetime
from typing import AsyncIterator

import alpaca_trade_api as tradeapi

from config.settings import get_settings
from layer4_execution.broker.base import BrokerAdapter
from layer4_execution.models import Order, OrderSide, OrderStatus
from shared.logging import get_logger

log = get_logger(__name__)


class AlpacaBroker(BrokerAdapter):
    def __init__(self) -> None:
        settings = get_settings()
        self._api = tradeapi.REST(
            key_id=settings.alpaca_api_key,
            secret_key=settings.alpaca_secret_key,
            base_url=settings.alpaca_base_url,
        )

    @property
    def name(self) -> str:
        return "alpaca"

    async def submit_order(
        self, ticker: str, side: OrderSide, quantity: int, limit_price: float | None = None
    ) -> Order:
        order_type = "limit" if limit_price else "market"
        kwargs = {
            "symbol": ticker,
            "qty": quantity,
            "side": side.value,
            "type": order_type,
            "time_in_force": "day",
        }
        if limit_price:
            kwargs["limit_price"] = str(limit_price)

        result = await asyncio.to_thread(self._api.submit_order, **kwargs)

        order = Order(
            order_id=result.id,
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=limit_price or 0,
            status=OrderStatus.PENDING,
        )

        log.info("order_submitted", order_id=order.order_id, ticker=ticker, side=side.value, qty=quantity)
        return order

    async def get_position(self, ticker: str) -> dict | None:
        try:
            pos = await asyncio.to_thread(self._api.get_position, ticker)
            return {
                "ticker": pos.symbol,
                "qty": int(pos.qty),
                "avg_entry": float(pos.avg_entry_price),
                "current_price": float(pos.current_price),
                "unrealized_pnl": float(pos.unrealized_pl),
                "market_value": float(pos.market_value),
            }
        except Exception:
            return None

    async def cancel_order(self, order_id: str) -> bool:
        try:
            await asyncio.to_thread(self._api.cancel_order, order_id)
            log.info("order_cancelled", order_id=order_id)
            return True
        except Exception as e:
            log.error("cancel_failed", order_id=order_id, error=str(e))
            return False

    async def get_account_info(self) -> dict:
        account = await asyncio.to_thread(self._api.get_account)
        return {
            "buying_power": float(account.buying_power),
            "equity": float(account.equity),
            "cash": float(account.cash),
            "portfolio_value": float(account.portfolio_value),
        }

    async def stream_price(self, ticker: str) -> AsyncIterator[float]:
        """Poll current price. For true streaming, use Alpaca websocket."""
        while True:
            try:
                pos = await self.get_position(ticker)
                if pos:
                    yield pos["current_price"]
                else:
                    quote = await asyncio.to_thread(
                        self._api.get_latest_trade, ticker
                    )
                    yield float(quote.price)
            except Exception as e:
                log.error("price_stream_error", ticker=ticker, error=str(e))
            await asyncio.sleep(5)
