"""SEC EDGAR RSS filing feed."""

from datetime import datetime

import aiohttp
import feedparser

from layer1_scanner.models import RawArticle
from layer1_scanner.sources.base import NewsSource
from shared.logging import get_logger

log = get_logger(__name__)

EDGAR_FULL_INDEX_RSS = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=8-K&dateb=&owner=include&count=20&search_text=&start=0&output=atom"


class SECEdgarSource(NewsSource):
    @property
    def name(self) -> str:
        return "sec_edgar"

    async def fetch(self) -> list[RawArticle]:
        try:
            headers = {"User-Agent": "TradingSignalSystem/1.0 (contact@example.com)"}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    EDGAR_FULL_INDEX_RSS,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    text = await resp.text()

            feed = feedparser.parse(text)
            articles = []
            for entry in feed.entries[:20]:
                published = None
                if hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])

                articles.append(RawArticle(
                    headline=entry.get("title", ""),
                    summary=entry.get("summary", ""),
                    source="sec_edgar",
                    url=entry.get("link", ""),
                    published_at=published,
                ))

            log.info("edgar_fetched", count=len(articles))
            return articles

        except Exception as e:
            log.error("edgar_fetch_error", error=str(e))
            return []
