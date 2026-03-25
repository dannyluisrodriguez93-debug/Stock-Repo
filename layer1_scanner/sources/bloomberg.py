"""Bloomberg news adapter (scrape/API placeholder)."""

import aiohttp

from layer1_scanner.models import RawArticle
from layer1_scanner.sources.base import NewsSource
from shared.logging import get_logger

log = get_logger(__name__)

BLOOMBERG_MARKETS_URL = "https://www.bloomberg.com/markets"


class BloombergSource(NewsSource):
    """Bloomberg source adapter.

    Note: Bloomberg does not offer a free RSS feed or public API.
    This adapter is a placeholder that can be extended with:
    - Bloomberg Terminal API (B-PIPE)
    - Bloomberg Enterprise Access Point
    - A custom scraping solution (respect ToS)
    """

    @property
    def name(self) -> str:
        return "bloomberg"

    async def fetch(self) -> list[RawArticle]:
        log.debug("bloomberg_fetch", msg="Bloomberg source is a placeholder; configure API access")
        return []
