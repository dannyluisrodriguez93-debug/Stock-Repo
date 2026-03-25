"""Shared test fixtures."""

import asyncio
import pytest

from shared.event_bus import EventBus


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
