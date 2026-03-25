"""Interactive Brokers adapter using ib_insync."""

import asyncio
from typing import AsyncIterator

from ib_insync import IB, MarketOrder, LimitOrder, Stock

from config.settings import get_settings
from layer4_execution.broker.base import BrokerAdapter
from layer4_execution.models import Order, OrderSide, OrderStatus
from shared.logging import get_logger

log = get_logger(__name__)


class IBKRBroker(BrokerAdapter):
    def __init__(self) -> None:
        settings = get_settings()
        self._ib = IB()
        self._host = settings.ibkr_host
        self._port = settings.ibkr_port
        self._client_id = settings.ibkr_client_id
        self._connected = False

    @property
    def name(self) -> str:
        return "ibkr"

    async def _ensure_connected(self) -> None:
        if not self._connected:
            await asyncio.to_thread(
                self._ib.connect, self._host, self._port, clientId=self._client_id
            )
            self._connected = True
            log.info("ibkr_connected")

    async def submit_order(
        self, ticker: str, side: OrderSide, quantity: int, limit_price: float | None = None
    ) -> Order:
        await self._ensure_connected()

        contract = Stock(ticker, "SMART", "USD")
        action = "BUY" if side == OrderSide.BUY else "SELL"

        if limit_price:
            ib_order = LimitOrder(action, quantity, limit_price)
        else:
            ib_order = MarketOrder(action, quantity)

        trade = await asyncio.to_thread(self._ib.placeOrder, contract, ib_order)

        order = Order(
            order_id=str(trade.order.orderId),
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=limit_price or 0,
            status=OrderStatus.PENDING,
        )

        log.info("ibkr_order_submitted", order_id=order.order_id, ticker=ticker)
        return order

    async def get_position(self, ticker: str) -> dict | None:
        await self._ensure_connected()
        positions = await asyncio.to_thread(self._ib.positions)
        for pos in positions:
            if pos.contract.symbol == ticker:
                return {
                    "ticker": ticker,
                    "qty": int(pos.position),
                    "avg_entry": float(pos.avgCost),
                    "current_price": 0.0,
                    "unrealized_pnl": 0.0,
                }
        return None

    async def cancel_order(self, order_id: str) -> bool:
        await self._ensure_connected()
        for trade in self._ib.openTrades():
            if str(trade.order.orderId) == order_id:
                await asyncio.to_thread(self._ib.cancelOrder, trade.order)
                return True
        return False

    async def get_account_info(self) -> dict:
        await self._ensure_connected()
        summary = await asyncio.to_thread(self._ib.accountSummary)
        info = {}
        for item in summary:
            info[item.tag] = item.value
        return info

    async def stream_price(self, ticker: str) -> AsyncIterator[float]:
        await self._ensure_connected()
        contract = Stock(ticker, "SMART", "USD")
        await asyncio.to_thread(self._ib.qualifyContracts, contract)

        self._ib.reqMktData(contract)
        while True:
            await asyncio.sleep(2)
            tick = self._ib.ticker(contract)
            if tick and tick.last:
                yield float(tick.last)
