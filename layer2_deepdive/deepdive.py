"""Layer 2 - Orchestrates technical + volume analysis for confirmed signals."""

import asyncio

from config.settings import get_settings
from layer1_scanner.models import ClassifiedSignal
from layer2_deepdive.data_feed import DataFeed
from layer2_deepdive.models import TradeSetup
from layer2_deepdive.technical import TechnicalAnalyzer
from layer2_deepdive.volume import VolumeMonitor
from shared.db import Database
from shared.event_bus import DEEPDIVE_TO_ALERT, SCANNER_TO_DEEPDIVE, EventBus
from shared.logging import get_logger

log = get_logger(__name__)


class DeepDiveAnalyzer:
    """Receives RED flag signals and runs deep analysis."""

    def __init__(self, event_bus: EventBus, db: Database) -> None:
        self._event_bus = event_bus
        self._db = db
        self._data_feed = DataFeed()
        self._technical = TechnicalAnalyzer(self._data_feed)
        self._volume = VolumeMonitor(self._data_feed)
        self._running = False

    async def _analyze_ticker(self, ticker: str, signal: ClassifiedSignal) -> TradeSetup | None:
        """Run technical and volume analysis in parallel. Both must confirm."""
        log.info("deepdive_started", ticker=ticker, catalyst=signal.catalyst_type)

        tech_task = self._technical.analyze(ticker)
        vol_task = self._volume.check_spike(ticker)

        tech_result, vol_result = await asyncio.gather(tech_task, vol_task, return_exceptions=True)

        if isinstance(tech_result, Exception):
            log.error("technical_failed", ticker=ticker, error=str(tech_result))
            return None
        if isinstance(vol_result, Exception):
            log.error("volume_failed", ticker=ticker, error=str(vol_result))
            return None

        if not tech_result.confirmed or not vol_result.confirmed:
            log.info(
                "deepdive_not_confirmed",
                ticker=ticker,
                technical=tech_result.confirmed,
                volume=vol_result.confirmed,
            )
            return None

        # Compute trade setup
        settings = get_settings()
        atr_mult = settings.technical.atr_stop_multiplier

        if signal.direction == "bullish":
            entry = tech_result.current_price
            target = tech_result.resistance
            stop_loss = tech_result.support - (entry * atr_mult / 100)
        else:
            entry = tech_result.current_price
            target = tech_result.support
            stop_loss = tech_result.resistance + (entry * atr_mult / 100)

        setup = TradeSetup(
            ticker=ticker,
            direction=signal.direction,
            entry_price=round(entry, 2),
            target_price=round(target, 2),
            stop_loss=round(stop_loss, 2),
            catalyst_type=signal.catalyst_type,
            catalyst_summary=signal.headline,
            confidence=signal.confidence,
            time_horizon=signal.time_horizon,
            technical=tech_result,
            volume=vol_result,
            signal=signal,
        )

        log.info(
            "trade_setup_computed",
            ticker=ticker,
            entry=setup.entry_price,
            target=setup.target_price,
            stop_loss=setup.stop_loss,
        )

        return setup

    async def _process_signal(self, signal: ClassifiedSignal) -> None:
        """Process a single RED flag signal, analyzing each ticker."""
        for ticker in signal.tickers:
            setup = await self._analyze_ticker(ticker, signal)
            if setup:
                # Log trade to DB
                await self._db.insert_trade(
                    ticker=setup.ticker,
                    direction=setup.direction,
                    entry_price=setup.entry_price,
                    target_price=setup.target_price,
                    stop_loss=setup.stop_loss,
                    status="pending_approval",
                )
                await self._event_bus.publish(DEEPDIVE_TO_ALERT, setup)

    async def run(self) -> None:
        """Main deep dive consumer loop."""
        self._running = True
        log.info("deepdive_consumer_started")

        while self._running:
            try:
                signal = await self._event_bus.subscribe(SCANNER_TO_DEEPDIVE)
                await self._process_signal(signal)
            except Exception as e:
                log.error("deepdive_error", error=str(e))

    def stop(self) -> None:
        self._running = False
