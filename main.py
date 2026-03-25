"""Trading Signal System - Main Orchestrator.

Wires all four layers together via async queues:
  Layer 1 (Scanner) → Layer 2 (Deep Dive) → Layer 3 (Alert) → Layer 4 (Execution)
"""

import asyncio
import signal
import sys

from config.settings import get_settings
from layer1_scanner.scanner import NewsScanner
from layer2_deepdive.deepdive import DeepDiveAnalyzer
from layer3_alert.alert import AlertManager
from layer4_execution.executor import TradeExecutor
from shared.db import Database
from shared.event_bus import EventBus
from shared.logging import get_logger, setup_logging


async def main() -> None:
    settings = get_settings()

    # Initialize logging
    setup_logging(level=settings.logging.level, json_output=settings.logging.json_output)
    log = get_logger("main")
    log.info("system_starting", broker=settings.execution.broker, paper=settings.execution.paper_trading)

    # Initialize shared infrastructure
    event_bus = EventBus()
    db = Database(settings.database.path)
    await db.connect()

    # Initialize all layers
    scanner = NewsScanner(event_bus, db)
    deepdive = DeepDiveAnalyzer(event_bus, db)
    alert_manager = AlertManager(event_bus, db)
    executor = TradeExecutor(event_bus, db)

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig, frame):
        log.info("shutdown_requested", signal=sig)
        scanner.stop()
        deepdive.stop()
        alert_manager.stop()
        executor.stop()
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    log.info("system_started", msg="All layers active. Scanning for signals...")

    # Run all layers concurrently
    try:
        await asyncio.gather(
            scanner.run(),       # Layer 1: polls news sources every 30-60s
            deepdive.run(),      # Layer 2: consumes RED flags, runs analysis
            alert_manager.run(), # Layer 3: sends alerts, waits for approval
            executor.run(),      # Layer 4: executes approved trades, monitors positions
        )
    except asyncio.CancelledError:
        log.info("tasks_cancelled")
    finally:
        await db.close()
        log.info("system_shutdown_complete")


if __name__ == "__main__":
    asyncio.run(main())
