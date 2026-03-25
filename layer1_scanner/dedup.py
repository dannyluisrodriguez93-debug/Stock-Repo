"""Entity-hash deduplication for news articles."""

import hashlib
import re
import time

from layer1_scanner.models import RawArticle
from shared.logging import get_logger

log = get_logger(__name__)


class Deduplicator:
    """Deduplicates articles by hashing normalized headline entities."""

    def __init__(self, ttl_hours: int = 24) -> None:
        self._seen: dict[str, float] = {}
        self._ttl_seconds = ttl_hours * 3600

    def _normalize(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9\s]", "", text)
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "of", "and", "or"}
        words = [w for w in text.split() if w not in stop_words]
        return " ".join(sorted(words))

    def _hash_article(self, article: RawArticle) -> str:
        normalized = self._normalize(article.headline)
        date_str = ""
        if article.published_at:
            date_str = article.published_at.strftime("%Y-%m-%d")
        key = f"{normalized}|{date_str}"
        return hashlib.sha256(key.encode()).hexdigest()

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, ts in self._seen.items() if now - ts > self._ttl_seconds]
        for k in expired:
            del self._seen[k]

    def is_duplicate(self, article: RawArticle) -> bool:
        self._evict_expired()
        h = self._hash_article(article)
        if h in self._seen:
            log.debug("duplicate_detected", headline=article.headline[:80])
            return True
        self._seen[h] = time.time()
        return False

    def filter_new(self, articles: list[RawArticle]) -> list[RawArticle]:
        return [a for a in articles if not self.is_duplicate(a)]

    @property
    def seen_count(self) -> int:
        return len(self._seen)
