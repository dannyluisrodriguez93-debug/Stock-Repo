"""Data models for Layer 2 - Ticker Deep Dive."""

from pydantic import BaseModel

from layer1_scanner.models import ClassifiedSignal


class TechnicalResult(BaseModel):
    """Results of technical analysis."""
    support: float
    resistance: float
    rsi: float
    vwap: float
    current_price: float
    trend: str  # "bullish", "bearish", "neutral"
    bid_ask_spread: float = 0.0
    confirmed: bool = False


class VolumeResult(BaseModel):
    """Results of volume monitoring."""
    current_volume: float
    avg_volume_20d: float
    spike_ratio: float
    sustained: bool = False
    confirmed: bool = False


class TradeSetup(BaseModel):
    """Computed trade entry/exit parameters."""
    ticker: str
    direction: str
    entry_price: float
    target_price: float
    stop_loss: float
    catalyst_type: str
    catalyst_summary: str
    confidence: float
    time_horizon: str
    technical: TechnicalResult
    volume: VolumeResult
    signal: ClassifiedSignal
