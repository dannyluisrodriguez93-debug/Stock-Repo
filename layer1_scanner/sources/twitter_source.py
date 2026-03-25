"""Twitter/X filtered stream source using Tweepy."""

import tweepy
import asyncio
from datetime import datetime

from layer1_scanner.models import RawArticle
from layer1_scanner.sources.base import NewsSource
from shared.logging import get_logger

log = get_logger(__name__)

# Accounts and keywords relevant to market-moving news
DEFAULT_ACCOUNTS = [
    "Reuters", "business", "DeItaone", "FirstSquawk",
    "LiveSquawk", "zabormeister", "BreakingNews",
]

DEFAULT_KEYWORDS = [
    "breaking", "FDA approval", "contract award", "earnings",
    "SEC filing", "merger", "acquisition", "sanctions",
    "tariff", "defense contract",
]


class TwitterSource(NewsSource):
    def __init__(self, bearer_token: str) -> None:
        self._bearer_token = bearer_token
        self._client: tweepy.Client | None = None
        self._recent_tweets: list[RawArticle] = []

    @property
    def name(self) -> str:
        return "twitter"

    def _get_client(self) -> tweepy.Client:
        if self._client is None:
            self._client = tweepy.Client(bearer_token=self._bearer_token)
        return self._client

    async def fetch(self) -> list[RawArticle]:
        if not self._bearer_token:
            log.warning("twitter_no_token", msg="Twitter bearer token not configured")
            return []

        try:
            client = self._get_client()
            query = " OR ".join(f'"{kw}"' for kw in DEFAULT_KEYWORDS[:5])
            query += " lang:en -is:retweet"

            response = await asyncio.to_thread(
                client.search_recent_tweets,
                query=query,
                max_results=20,
                tweet_fields=["created_at", "author_id", "text"],
            )

            articles = []
            if response.data:
                for tweet in response.data:
                    articles.append(RawArticle(
                        headline=tweet.text[:200],
                        summary=tweet.text,
                        source="twitter",
                        url=f"https://x.com/i/status/{tweet.id}",
                        published_at=tweet.created_at,
                    ))

            log.info("twitter_fetched", count=len(articles))
            return articles

        except Exception as e:
            log.error("twitter_fetch_error", error=str(e))
            return []
