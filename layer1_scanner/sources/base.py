"""Abstract base class for news sources."""

from abc import ABC, abstractmethod

from layer1_scanner.models import RawArticle


class NewsSource(ABC):
    """Base class for all news feed sources."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def fetch(self) -> list[RawArticle]:
        """Fetch latest articles from this source."""
        ...
