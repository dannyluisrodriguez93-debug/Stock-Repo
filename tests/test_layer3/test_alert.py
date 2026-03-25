"""Tests for Layer 3 alert formatting."""

from layer1_scanner.models import ClassifiedSignal, FlagLevel
from layer2_deepdive.models import TechnicalResult, TradeSetup, VolumeResult
from layer3_alert.models import AlertPayload


def _make_setup() -> TradeSetup:
    tech = TechnicalResult(
        support=145.0, resistance=175.0, rsi=65.0,
        vwap=158.0, current_price=162.0, trend="bullish", confirmed=True,
    )
    vol = VolumeResult(
        current_volume=8_000_000, avg_volume_20d=3_000_000,
        spike_ratio=2.67, sustained=True, confirmed=True,
    )
    signal = ClassifiedSignal(
        tickers=["BA"], direction="bullish", catalyst_type="contract_win",
        magnitude=4, confidence=0.82, flag_level=FlagLevel.RED,
    )
    return TradeSetup(
        ticker="BA",
        direction="bullish",
        entry_price=162.0,
        target_price=175.0,
        stop_loss=143.38,
        catalyst_type="contract_win",
        catalyst_summary="Boeing wins $10B defense contract",
        confidence=0.82,
        time_horizon="1-3 days",
        technical=tech,
        volume=vol,
        signal=signal,
    )


def test_alert_payload_from_setup():
    setup = _make_setup()
    payload = AlertPayload.from_trade_setup(setup)
    assert payload.ticker == "BA"
    assert payload.entry_price == 162.0
    assert payload.confidence == 0.82


def test_alert_message_format():
    setup = _make_setup()
    payload = AlertPayload.from_trade_setup(setup)
    msg = payload.format_message()
    assert "BA" in msg
    assert "LONG" in msg
    assert "$162.00" in msg
    assert "$175.00" in msg
    assert "GO" in msg
    assert "Boeing" in msg
