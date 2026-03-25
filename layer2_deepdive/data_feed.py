"""Market data feed using yfinance with caching."""

import asyncio
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from shared.exceptions import DataFeedError
from shared.logging import get_logger

log = get_logger(__name__)


class DataFeed:
    """Fetches OHLCV data with simple TTL cache."""

    def __init__(self, cache_ttl_sec: int = 300) -> None:
        self._cache: dict[str, tuple[pd.DataFrame, float]] = {}
        self._cache_ttl = cache_ttl_sec

    def _cache_key(self, ticker: str, period: str, interval: str) -> str:
        return f"{ticker}|{period}|{interval}"

    async def get_ohlcv(
        self,
        ticker: str,
        period: str = "30d",
        interval: str = "5m",
    ) -> pd.DataFrame:
        """Fetch OHLCV data. Returns DataFrame with Open, High, Low, Close, Volume."""
        key = self._cache_key(ticker, period, interval)

        if key in self._cache:
            df, ts = self._cache[key]
            if time.time() - ts < self._cache_ttl:
                log.debug("cache_hit", ticker=ticker)
                return df

        try:
            stock = yf.Ticker(ticker)
            df = await asyncio.to_thread(stock.history, period=period, interval=interval)

            if df.empty:
                raise DataFeedError(f"No data returned for {ticker}")

            self._cache[key] = (df, time.time())
            log.info("data_fetched", ticker=ticker, rows=len(df), period=period, interval=interval)
            return df

        except DataFeedError:
            raise
        except Exception as e:
            raise DataFeedError(f"Failed to fetch data for {ticker}: {e}") from e

    async def get_current_price(self, ticker: str) -> float:
        """Get the most recent closing price."""
        df = await self.get_ohlcv(ticker, period="1d", interval="1m")
        return float(df["Close"].iloc[-1])

    async def get_quote(self, ticker: str) -> dict:
        """Get current bid/ask and other quote data."""
        try:
            stock = yf.Ticker(ticker)
            info = await asyncio.to_thread(lambda: stock.info)
            return {
                "bid": info.get("bid", 0),
                "ask": info.get("ask", 0),
                "spread": info.get("ask", 0) - info.get("bid", 0),
                "volume": info.get("volume", 0),
                "avg_volume": info.get("averageVolume", 0),
            }
        except Exception as e:
            log.error("quote_error", ticker=ticker, error=str(e))
            return {}
