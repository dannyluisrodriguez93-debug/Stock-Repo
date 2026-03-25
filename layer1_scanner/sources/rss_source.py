"""RSS-based news sources: Reuters, AP, Defense News, Google News."""

from datetime import datetime

import aiohttp
import feedparser

from layer1_scanner.models import RawArticle
from layer1_scanner.sources.base import NewsSource
from shared.logging import get_logger

log = get_logger(__name__)


class RSSSource(NewsSource):
    """Generic RSS feed source."""

    def __init__(self, source_name: str, feed_url: str) -> None:
        self._name = source_name
        self._feed_url = feed_url

    @property
    def name(self) -> str:
        return self._name

    async def fetch(self) -> list[RawArticle]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self._feed_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    text = await resp.text()

            feed = feedparser.parse(text)
            articles = []
            for entry in feed.entries[:20]:
                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])

                articles.append(RawArticle(
                    headline=entry.get("title", ""),
                    summary=entry.get("summary", ""),
                    source=self._name,
                    url=entry.get("link", ""),
                    published_at=published,
                ))

            log.info("rss_fetched", source=self._name, count=len(articles))
            return articles

        except Exception as e:
            log.error("rss_fetch_error", source=self._name, error=str(e))
            return []


class ReutersRSS(RSSSource):
    def __init__(self) -> None:
        super().__init__("reuters", "https://feeds.reuters.com/reuters/businessNews")


class APRSS(RSSSource):
    def __init__(self) -> None:
        super().__init__("ap", "https://rsshub.app/apnews/topics/business")


class DefenseNewsRSS(RSSSource):
    def __init__(self) -> None:
        super().__init__("defense_news", "https://www.defensenews.com/arc/outboundfeeds/rss/")


class GoogleNewsRSS(RSSSource):
    def __init__(self) -> None:
        super().__init__(
            "google_news",
            "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB?hl=en-US&gl=US&ceid=US:en",
        )
