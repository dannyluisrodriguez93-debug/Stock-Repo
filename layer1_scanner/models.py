"""Data models for Layer 1 - News Scanner."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FlagLevel(str, Enum):
    NONE = "none"
    YELLOW = "yellow"
    RED = "red"


class RawArticle(BaseModel):
    """Raw article from a news source before classification."""
    headline: str
    summary: str = ""
    source: str
    url: str = ""
    published_at: datetime | None = None
    raw_text: str = ""


class ClassifiedSignal(BaseModel):
    """LLM-classified signal with trading metadata."""
    tickers: list[str]
    direction: str = Field(description="bullish or bearish")
    catalyst_type: str = Field(description="geopolitical, earnings, regulatory, supply_chain, contract_win")
    magnitude: int = Field(ge=1, le=5, description="Impact magnitude 1-5")
    confidence: float = Field(ge=0.0, le=1.0)
    time_horizon: str = ""
    flag_level: FlagLevel = FlagLevel.NONE
    headline: str = ""
    source: str = ""
    source_count: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def escalate(self) -> None:
        """Escalate yellow to red when more sources confirm."""
        if self.flag_level == FlagLevel.YELLOW:
            self.flag_level = FlagLevel.RED
