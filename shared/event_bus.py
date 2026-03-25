"""Async queue-based inter-layer message passing."""

import asyncio
from typing import Any

from shared.logging import get_logger

log = get_logger(__name__)


class EventBus:
    """Named async queues for inter-layer communication."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    def get_queue(self, name: str) -> asyncio.Queue:
        if name not in self._queues:
            self._queues[name] = asyncio.Queue()
            log.info("queue_created", queue=name)
        return self._queues[name]

    async def publish(self, queue_name: str, message: Any) -> None:
        q = self.get_queue(queue_name)
        await q.put(message)
        log.info("message_published", queue=queue_name, type=type(message).__name__)

    async def subscribe(self, queue_name: str) -> Any:
        q = self.get_queue(queue_name)
        message = await q.get()
        log.info("message_received", queue=queue_name, type=type(message).__name__)
        return message


# Queue name constants
SCANNER_TO_DEEPDIVE = "scanner_to_deepdive"
DEEPDIVE_TO_ALERT = "deepdive_to_alert"
ALERT_TO_EXECUTION = "alert_to_execution"
