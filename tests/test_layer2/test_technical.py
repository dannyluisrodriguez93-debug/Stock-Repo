"""Tests for Layer 2 technical analysis models."""

from layer2_deepdive.models import TechnicalResult, VolumeResult, TradeSetup
from layer1_scanner.models import ClassifiedSignal, FlagLevel


def test_technical_result_confirmed():
    result = TechnicalResult(
        support=150.0,
        resistance=170.0,
        rsi=62.5,
        vwap=158.0,
        current_price=160.0,
        trend="bullish",
        confirmed=True,
    )
    assert result.confirmed
    assert result.trend == "bullish"


def test_volume_result_spike():
    result = VolumeResult(
        current_volume=5_000_000,
        avg_volume_20d=2_000_000,
        spike_ratio=2.5,
        sustained=True,
        confirmed=True,
    )
    assert result.spike_ratio == 2.5
    assert result.confirmed


def test_trade_setup_creation():
    tech = TechnicalResult(
        support=148.0, resistance=172.0, rsi=58.0,
        vwap=155.0, current_price=165.0, trend="bullish", confirmed=True,
    )
    vol = VolumeResult(
        current_volume=6_000_000, avg_volume_20d=2_000_000,
        spike_ratio=3.0, sustained=True, confirmed=True,
    )
    signal = ClassifiedSignal(
        tickers=["AAPL"], direction="bullish", catalyst_type="earnings",
        magnitude=4, confidence=0.85, flag_level=FlagLevel.RED,
    )

    setup = TradeSetup(
        ticker="AAPL",
        direction="bullish",
        entry_price=165.0,
        target_price=172.0,
        stop_loss=146.35,
        catalyst_type="earnings",
        catalyst_summary="Apple beats earnings",
        confidence=0.85,
        time_horizon="2 days",
        technical=tech,
        volume=vol,
        signal=signal,
    )

    assert setup.ticker == "AAPL"
    assert setup.entry_price == 165.0
    assert setup.target_price > setup.entry_price
    assert setup.stop_loss < setup.entry_price
