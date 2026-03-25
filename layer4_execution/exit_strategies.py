"""Exit strategy implementations: take-profit, trailing stop, time decay, volume divergence."""

import asyncio
from datetime import datetime, timedelta

import numpy as np

from config.settings import get_settings
from layer2_deepdive.data_feed import DataFeed
from layer4_execution.models import ExitTrigger, Position
from shared.logging import get_logger

log = get_logger(__name__)


async def take_profit_monitor(
    position: Position,
    price_stream: asyncio.Queue,
) -> tuple[ExitTrigger, float, float]:
    """Monitor for take-profit. Supports scaled exits for wide targets (6%+)."""
    settings = get_settings().exit
    threshold = settings.scaled_exit_threshold_pct / 100.0
    entry = position.entry_price
    target = position.target_price
    target_pct = abs(target - entry) / entry

    total_qty = position.quantity
    sold_qty = 0

    if target_pct >= threshold:
        # Scaled exit
        levels = settings.scaled_exit_levels
        next_level_idx = 0

        while True:
            price = await price_stream.get()
            gain_pct = (price - entry) / entry if position.direction == "bullish" else (entry - price) / entry

            while next_level_idx < len(levels):
                level = levels[next_level_idx]
                if gain_pct >= level.pct / 100.0:
                    sell_qty = int(total_qty * level.sell_fraction)
                    sold_qty += sell_qty
                    log.info(
                        "scaled_exit_triggered",
                        ticker=position.ticker,
                        level_pct=level.pct,
                        sell_qty=sell_qty,
                    )
                    next_level_idx += 1

                    if sold_qty >= total_qty or next_level_idx >= len(levels):
                        return ExitTrigger.TAKE_PROFIT, price, float(sold_qty) / total_qty
                else:
                    break
    else:
        # Simple take-profit at target
        while True:
            price = await price_stream.get()
            if position.direction == "bullish" and price >= target:
                return ExitTrigger.TAKE_PROFIT, price, 1.0
            elif position.direction == "bearish" and price <= target:
                return ExitTrigger.TAKE_PROFIT, price, 1.0


async def trailing_stop_monitor(
    position: Position,
    price_stream: asyncio.Queue,
) -> tuple[ExitTrigger, float, float]:
    """Monitor trailing stop. Starts at 1.5% below entry, follows price up."""
    trail_pct = get_settings().exit.trailing_stop_pct / 100.0
    high_water = position.entry_price
    stop_price = high_water * (1 - trail_pct)

    while True:
        price = await price_stream.get()

        if position.direction == "bullish":
            if price > high_water:
                high_water = price
                stop_price = high_water * (1 - trail_pct)
            if price <= stop_price:
                log.info("trailing_stop_hit", ticker=position.ticker, price=price, stop=stop_price)
                return ExitTrigger.TRAILING_STOP, price, 1.0
        else:
            if price < high_water:
                high_water = price
                stop_price = high_water * (1 + trail_pct)
            if price >= stop_price:
                log.info("trailing_stop_hit", ticker=position.ticker, price=price, stop=stop_price)
                return ExitTrigger.TRAILING_STOP, price, 1.0


async def time_decay_monitor(
    position: Position,
) -> tuple[ExitTrigger, float, float]:
    """Force exit after max hold window based on catalyst type."""
    settings = get_settings().time_decay
    max_hours = settings.hours_for_catalyst(position.catalyst_type)
    deadline = position.opened_at + timedelta(hours=max_hours)

    now = datetime.utcnow()
    remaining = (deadline - now).total_seconds()

    if remaining > 0:
        log.info("time_decay_waiting", ticker=position.ticker, hours=max_hours, deadline=deadline.isoformat())
        await asyncio.sleep(remaining)

    log.info("time_decay_triggered", ticker=position.ticker)
    return ExitTrigger.TIME_DECAY, position.current_price, 1.0


async def volume_divergence_monitor(
    position: Position,
    data_feed: DataFeed,
) -> tuple[ExitTrigger, float, float]:
    """Exit if price rises but volume declines for N consecutive candles."""
    settings = get_settings().exit
    required_candles = settings.volume_divergence_candles
    consecutive_divergent = 0

    while True:
        await asyncio.sleep(300)  # Check every 5 minutes

        try:
            df = await data_feed.get_ohlcv(position.ticker, period="1d", interval="5m")
            if len(df) < required_candles + 1:
                continue

            recent = df.tail(required_candles + 1)
            prices = recent["Close"].values
            volumes = recent["Volume"].values

            # Check: price rising but volume declining
            price_rising = all(prices[i + 1] >= prices[i] for i in range(len(prices) - 1))
            volume_declining = all(volumes[i + 1] < volumes[i] for i in range(len(volumes) - 1))

            if price_rising and volume_declining:
                consecutive_divergent += 1
            else:
                consecutive_divergent = 0

            if consecutive_divergent >= 1:
                current_price = float(prices[-1])
                log.info(
                    "volume_divergence_triggered",
                    ticker=position.ticker,
                    price=current_price,
                )
                return ExitTrigger.VOLUME_DIVERGENCE, current_price, 1.0

        except Exception as e:
            log.error("volume_divergence_error", ticker=position.ticker, error=str(e))
