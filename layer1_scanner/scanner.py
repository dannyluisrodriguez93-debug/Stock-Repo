"""Layer 1 - Main news scanning loop with dedup and classification."""

import asyncio
from datetime import datetime

from config.settings import get_settings
from layer1_scanner.classifier import SignalClassifier
from layer1_scanner.dedup import Deduplicator
from layer1_scanner.models import ClassifiedSignal, FlagLevel, RawArticle
from layer1_scanner.sources.base import NewsSource
from layer1_scanner.sources.bloomberg import BloombergSource
from layer1_scanner.sources.rss_source import (
    APRSS,
    DefenseNewsRSS,
    GoogleNewsRSS,
    ReutersRSS,
)
from layer1_scanner.sources.sec_edgar import SECEdgarSource
from layer1_scanner.sources.twitter_source import TwitterSource
from shared.db import Database
from shared.event_bus import SCANNER_TO_DEEPDIVE, EventBus
from shared.logging import get_logger

log = get_logger(__name__)


class NewsScanner:
    """Orchestrates polling, dedup, classification, and signal scoring."""

    def __init__(self, event_bus: EventBus, db: Database) -> None:
        self._settings = get_settings()
        self._event_bus = event_bus
        self._db = db
        self._dedup = Deduplicator(ttl_hours=self._settings.dedup.ttl_hours)
        self._classifier = SignalClassifier()
        self._sources = self._init_sources()
        self._signal_buffer: dict[str, ClassifiedSignal] = {}
        self._running = False

    def _init_sources(self) -> list[NewsSource]:
        settings = self._settings
        sources: list[NewsSource] = []
        source_map = {
            "reuters_rss": ReutersRSS,
            "ap_rss": APRSS,
            "google_news_rss": GoogleNewsRSS,
            "defense_news_rss": DefenseNewsRSS,
            "sec_edgar": SECEdgarSource,
            "bloomberg": BloombergSource,
        }
        for name in settings.scanner.sources:
            if name == "twitter":
                sources.append(TwitterSource(settings.twitter_bearer_token))
            elif name in source_map:
                sources.append(source_map[name]())
            else:
                log.warning("unknown_source", source=name)
        return sources

    async def _fetch_all_sources(self) -> list[RawArticle]:
        """Fan out to all sources concurrently."""
        tasks = [source.fetch() for source in self._sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        articles = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log.error("source_error", source=self._sources[i].name, error=str(result))
            else:
                articles.extend(result)

        return articles

    def _score_and_merge(self, signals: list[ClassifiedSignal]) -> list[ClassifiedSignal]:
        """Merge signals targeting the same tickers, boost confidence on multi-source confirmation."""
        for signal in signals:
            for ticker in signal.tickers:
                key = f"{ticker}|{signal.catalyst_type}|{signal.direction}"
                if key in self._signal_buffer:
                    existing = self._signal_buffer[key]
                    existing.source_count += 1
                    existing.confidence = min(1.0, existing.confidence + 0.1)
                    if existing.source_count >= 2 and existing.flag_level == FlagLevel.YELLOW:
                        existing.escalate()
                        log.info("signal_escalated", ticker=ticker, sources=existing.source_count)
                else:
                    self._signal_buffer[key] = signal

        return list(self._signal_buffer.values())

    async def _process_cycle(self) -> None:
        """Single scan cycle: fetch → dedup → classify → score → emit."""
        articles = await self._fetch_all_sources()
        log.info("scan_cycle", total_articles=len(articles), dedup_seen=self._dedup.seen_count)

        new_articles = self._dedup.filter_new(articles)
        if not new_articles:
            return

        log.info("new_articles", count=len(new_articles))

        signals = await self._classifier.classify_batch(new_articles)
        if not signals:
            return

        scored = self._score_and_merge(signals)

        for signal in scored:
            # Log to DB
            await self._db.insert_signal(
                timestamp=signal.timestamp.isoformat(),
                tickers=",".join(signal.tickers),
                direction=signal.direction,
                catalyst_type=signal.catalyst_type,
                magnitude=signal.magnitude,
                confidence=signal.confidence,
                flag_level=signal.flag_level.value,
                headline=signal.headline,
                source=signal.source,
            )

            if signal.flag_level == FlagLevel.RED:
                log.info(
                    "RED_FLAG",
                    tickers=signal.tickers,
                    catalyst=signal.catalyst_type,
                    confidence=signal.confidence,
                )
                await self._event_bus.publish(SCANNER_TO_DEEPDIVE, signal)
                # Remove from buffer once escalated
                for ticker in signal.tickers:
                    key = f"{ticker}|{signal.catalyst_type}|{signal.direction}"
                    self._signal_buffer.pop(key, None)

            elif signal.flag_level == FlagLevel.YELLOW:
                log.info(
                    "YELLOW_FLAG",
                    tickers=signal.tickers,
                    catalyst=signal.catalyst_type,
                    confidence=signal.confidence,
                )

    async def run(self) -> None:
        """Main scanning loop."""
        self._running = True
        interval = self._settings.scanner.poll_interval_sec
        log.info("scanner_started", interval=interval, sources=len(self._sources))

        while self._running:
            try:
                await self._process_cycle()
            except Exception as e:
                log.error("scan_cycle_error", error=str(e))

            await asyncio.sleep(interval)

    def stop(self) -> None:
        self._running = False
        log.info("scanner_stopped")
