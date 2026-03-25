"""Tests for Layer 1 deduplication."""

from datetime import datetime

from layer1_scanner.dedup import Deduplicator
from layer1_scanner.models import RawArticle


def _article(headline: str, source: str = "reuters") -> RawArticle:
    return RawArticle(
        headline=headline,
        summary="test",
        source=source,
        published_at=datetime(2024, 1, 15),
    )


def test_new_article_not_duplicate():
    dedup = Deduplicator()
    article = _article("Apple reports record quarterly earnings")
    assert not dedup.is_duplicate(article)


def test_same_headline_is_duplicate():
    dedup = Deduplicator()
    a1 = _article("Apple reports record quarterly earnings")
    a2 = _article("Apple reports record quarterly earnings")
    dedup.is_duplicate(a1)
    assert dedup.is_duplicate(a2)


def test_different_source_same_headline_is_duplicate():
    dedup = Deduplicator()
    a1 = _article("Boeing wins $5B defense contract", source="reuters")
    a2 = _article("Boeing wins $5B defense contract", source="ap")
    dedup.is_duplicate(a1)
    assert dedup.is_duplicate(a2)


def test_different_headlines_not_duplicate():
    dedup = Deduplicator()
    a1 = _article("Apple reports record earnings")
    a2 = _article("Tesla announces new factory")
    dedup.is_duplicate(a1)
    assert not dedup.is_duplicate(a2)


def test_filter_new_removes_duplicates():
    dedup = Deduplicator()
    articles = [
        _article("Breaking news about AAPL"),
        _article("Breaking news about AAPL"),
        _article("Different story about TSLA"),
    ]
    filtered = dedup.filter_new(articles)
    assert len(filtered) == 2


def test_seen_count():
    dedup = Deduplicator()
    dedup.is_duplicate(_article("Article 1"))
    dedup.is_duplicate(_article("Article 2"))
    assert dedup.seen_count == 2
