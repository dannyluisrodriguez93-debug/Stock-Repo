"""Position monitoring with parallel exit triggers. First trigger wins."""

import asyncio
from datetime import datetime

from layer2_deepdive.data_feed import DataFeed
from layer4_execution.broker.base import BrokerAdapter
from layer4_execution.exit_strategies import (
    take_profit_monitor,
    time_decay_monitor,
    trailing_stop_monitor,
    volume_divergence_monitor,
)
from layer4_execution.models import ExitTrigger, ExecutionResult, OrderSide, Position
from shared.db import Database
from shared.logging import get_logger

log = get_logger(__name__)


class PositionMonitor:
    """Monitors an open position with parallel exit triggers."""

    def __init__(self, broker: BrokerAdapter, db: Database) -> None:
        self._broker = broker
        self._db = db
        self._data_feed = DataFeed()

    async def _feed_prices(self, ticker: str, queues: list[asyncio.Queue]) -> None:
        """Stream prices and fan out to all exit strategy queues."""
        async for price in self._broker.stream_price(ticker):
            for q in queues:
                await q.put(price)

    async def monitor(self, position: Position, trade_id: int) -> ExecutionResult:
        """Run all exit triggers in parallel. First one to fire wins."""
        log.info(
            "monitoring_started",
            ticker=position.ticker,
            entry=position.entry_price,
            target=position.target_price,
            stop_loss=position.stop_loss,
        )

        # Create price stream queues for each price-dependent strategy
        tp_queue: asyncio.Queue = asyncio.Queue()
        ts_queue: asyncio.Queue = asyncio.Queue()
        price_queues = [tp_queue, ts_queue]

        # Launch price feeder
        feeder = asyncio.create_task(self._feed_prices(position.ticker, price_queues))

        # Launch all exit strategy tasks
        tasks = {
            asyncio.create_task(take_profit_monitor(position, tp_queue)): "take_profit",
            asyncio.create_task(trailing_stop_monitor(position, ts_queue)): "trailing_stop",
            asyncio.create_task(time_decay_monitor(position)): "time_decay",
            asyncio.create_task(volume_divergence_monitor(position, self._data_feed)): "volume_divergence",
        }

        try:
            # Wait for FIRST trigger to complete
            done, pending = await asyncio.wait(
                tasks.keys(), return_when=asyncio.FIRST_COMPLETED
            )

            # Get the winning trigger
            winner = done.pop()
            trigger, exit_price, sell_fraction = winner.result()

            log.info(
                "EXIT_TRIGGERED",
                ticker=position.ticker,
                trigger=trigger.value,
                exit_price=exit_price,
                sell_fraction=sell_fraction,
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            feeder.cancel()

            # Execute sell order
            sell_qty = int(position.quantity * sell_fraction)
            if sell_qty > 0:
                side = OrderSide.SELL if position.direction == "bullish" else OrderSide.BUY
                await self._broker.submit_order(
                    position.ticker, side, sell_qty
                )

            # Compute P&L
            if position.direction == "bullish":
                pnl = (exit_price - position.entry_price) * sell_qty
            else:
                pnl = (position.entry_price - exit_price) * sell_qty
            pnl_pct = pnl / (position.entry_price * sell_qty) * 100 if sell_qty > 0 else 0

            held = (datetime.utcnow() - position.opened_at).total_seconds()

            result = ExecutionResult(
                ticker=position.ticker,
                entry_price=position.entry_price,
                exit_price=exit_price,
                exit_trigger=trigger,
                quantity=sell_qty,
                pnl=round(pnl, 2),
                pnl_pct=round(pnl_pct, 2),
                held_duration_sec=held,
            )

            # Update DB
            await self._db.update_trade(
                trade_id,
                exit_price=exit_price,
                exit_trigger=trigger.value,
                pnl=result.pnl,
                status="closed",
                closed_at=datetime.utcnow().isoformat(),
            )

            log.info(
                "TRADE_CLOSED",
                ticker=result.ticker,
                pnl=result.pnl,
                pnl_pct=result.pnl_pct,
                trigger=result.exit_trigger.value,
                held_sec=result.held_duration_sec,
            )

            return result

        except Exception as e:
            log.error("monitor_error", ticker=position.ticker, error=str(e))
            feeder.cancel()
            for task in tasks:
                task.cancel()
            raise
