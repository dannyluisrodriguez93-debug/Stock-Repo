"""Technical analysis: support/resistance, RSI, VWAP, bid-ask."""

import numpy as np
import pandas as pd
import pandas_ta as ta

from config.settings import get_settings
from layer2_deepdive.data_feed import DataFeed
from layer2_deepdive.models import TechnicalResult
from shared.logging import get_logger

log = get_logger(__name__)


class TechnicalAnalyzer:
    def __init__(self, data_feed: DataFeed) -> None:
        self._feed = data_feed
        self._settings = get_settings().technical

    def _find_support_resistance(self, df: pd.DataFrame) -> tuple[float, float]:
        """Find support and resistance via pivot point clustering."""
        highs = df["High"].values
        lows = df["Low"].values
        close = df["Close"].values

        # Simple pivot points
        pivot = (highs[-1] + lows[-1] + close[-1]) / 3
        r1 = 2 * pivot - lows[-1]
        s1 = 2 * pivot - highs[-1]

        # Cluster recent lows for support, recent highs for resistance
        recent_lows = sorted(lows[-20:])
        recent_highs = sorted(highs[-20:], reverse=True)

        support = float(np.median(recent_lows[:5])) if len(recent_lows) >= 5 else float(s1)
        resistance = float(np.median(recent_highs[:5])) if len(recent_highs) >= 5 else float(r1)

        return support, resistance

    def _compute_rsi(self, df: pd.DataFrame) -> float:
        rsi = ta.rsi(df["Close"], length=self._settings.rsi_period)
        if rsi is not None and not rsi.empty:
            return float(rsi.iloc[-1])
        return 50.0

    def _compute_vwap(self, df: pd.DataFrame) -> float:
        if not self._settings.vwap_enabled:
            return 0.0
        vwap = ta.vwap(df["High"], df["Low"], df["Close"], df["Volume"])
        if vwap is not None and not vwap.empty:
            return float(vwap.iloc[-1])
        return float(df["Close"].iloc[-1])

    def _determine_trend(self, df: pd.DataFrame, rsi: float) -> str:
        close = df["Close"]
        sma_20 = close.rolling(20).mean().iloc[-1]
        current = close.iloc[-1]

        if current > sma_20 and rsi > 50:
            return "bullish"
        elif current < sma_20 and rsi < 50:
            return "bearish"
        return "neutral"

    async def analyze(self, ticker: str) -> TechnicalResult:
        """Run full technical analysis on a ticker."""
        # Get 30-day daily data for support/resistance
        df_daily = await self._feed.get_ohlcv(ticker, period="30d", interval="1d")
        # Get intraday data for VWAP
        df_intraday = await self._feed.get_ohlcv(ticker, period="5d", interval="5m")

        current_price = float(df_daily["Close"].iloc[-1])
        support, resistance = self._find_support_resistance(df_daily)
        rsi = self._compute_rsi(df_daily)
        vwap = self._compute_vwap(df_intraday)
        trend = self._determine_trend(df_daily, rsi)

        # Get bid-ask spread
        quote = await self._feed.get_quote(ticker)
        spread = quote.get("spread", 0.0)

        # Confirmation: price near support (long) or resistance (short) + trend aligns
        proximity_pct = self._settings.entry_proximity_pct / 100.0
        price_at_support = abs(current_price - support) / current_price <= proximity_pct
        price_at_resistance = abs(current_price - resistance) / current_price <= proximity_pct
        breakout_above = current_price > resistance
        breakdown_below = current_price < support

        confirmed = (
            (breakout_above and trend == "bullish")
            or (breakdown_below and trend == "bearish")
            or (price_at_support and trend == "bullish")
            or (price_at_resistance and trend == "bearish")
        )

        result = TechnicalResult(
            support=round(support, 2),
            resistance=round(resistance, 2),
            rsi=round(rsi, 2),
            vwap=round(vwap, 2),
            current_price=round(current_price, 2),
            trend=trend,
            bid_ask_spread=round(spread, 4),
            confirmed=confirmed,
        )

        log.info(
            "technical_analysis",
            ticker=ticker,
            support=result.support,
            resistance=result.resistance,
            rsi=result.rsi,
            trend=result.trend,
            confirmed=result.confirmed,
        )

        return result
