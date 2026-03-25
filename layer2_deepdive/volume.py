"""Volume monitoring: spike detection and sustainability check."""

import asyncio

import numpy as np

from config.settings import get_settings
from layer2_deepdive.data_feed import DataFeed
from layer2_deepdive.models import VolumeResult
from shared.logging import get_logger

log = get_logger(__name__)


class VolumeMonitor:
    def __init__(self, data_feed: DataFeed) -> None:
        self._feed = data_feed
        self._settings = get_settings().deepdive

    async def check_spike(self, ticker: str) -> VolumeResult:
        """Check if current volume represents a spike vs 20-day average."""
        df = await self._feed.get_ohlcv(ticker, period="30d", interval="1d")

        volumes = df["Volume"].values
        avg_20d = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else float(np.mean(volumes))
        current_vol = float(volumes[-1])
        spike_ratio = current_vol / avg_20d if avg_20d > 0 else 0.0

        initial_spike = spike_ratio >= self._settings.volume_spike_threshold

        log.info(
            "volume_check",
            ticker=ticker,
            current=current_vol,
            avg_20d=avg_20d,
            ratio=round(spike_ratio, 2),
            spike=initial_spike,
        )

        if not initial_spike:
            return VolumeResult(
                current_volume=current_vol,
                avg_volume_20d=avg_20d,
                spike_ratio=round(spike_ratio, 2),
                sustained=False,
                confirmed=False,
            )

        # Monitor for sustainability within the window
        sustained = await self._monitor_sustainability(ticker, avg_20d)

        return VolumeResult(
            current_volume=current_vol,
            avg_volume_20d=avg_20d,
            spike_ratio=round(spike_ratio, 2),
            sustained=sustained,
            confirmed=initial_spike and sustained,
        )

    async def _monitor_sustainability(self, ticker: str, avg_20d: float) -> bool:
        """Monitor volume over a window to confirm spike sustains."""
        window_minutes = self._settings.volume_window_minutes
        poll_interval = self._settings.volume_poll_interval_sec
        checks = window_minutes * 60 // poll_interval
        confirms = 0
        threshold = self._settings.volume_spike_threshold

        log.info("volume_monitoring_started", ticker=ticker, window_min=window_minutes)

        for i in range(min(checks, 5)):  # Cap at 5 checks to avoid blocking too long
            await asyncio.sleep(poll_interval)

            try:
                df = await self._feed.get_ohlcv(ticker, period="1d", interval="5m")
                if df.empty:
                    continue

                latest_vol = float(df["Volume"].iloc[-1])
                # Normalize 5-min candle against per-candle average
                candles_per_day = 78  # ~6.5 hours * 12 candles/hour
                avg_per_candle = avg_20d / candles_per_day
                ratio = latest_vol / avg_per_candle if avg_per_candle > 0 else 0

                if ratio >= threshold:
                    confirms += 1
                    log.debug("volume_sustain_check", ticker=ticker, check=i + 1, ratio=round(ratio, 2), confirmed=True)

            except Exception as e:
                log.error("volume_monitor_error", ticker=ticker, error=str(e))

        sustained = confirms >= max(1, checks // 3)
        log.info("volume_monitoring_done", ticker=ticker, confirms=confirms, sustained=sustained)
        return sustained
