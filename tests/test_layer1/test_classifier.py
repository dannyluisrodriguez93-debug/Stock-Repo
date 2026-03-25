"""Tests for Layer 1 signal classification models."""

from layer1_scanner.models import ClassifiedSignal, FlagLevel


def test_flag_level_escalation():
    signal = ClassifiedSignal(
        tickers=["BA"],
        direction="bullish",
        catalyst_type="contract_win",
        magnitude=3,
        confidence=0.5,
        flag_level=FlagLevel.YELLOW,
        source_count=1,
    )
    signal.escalate()
    assert signal.flag_level == FlagLevel.RED


def test_red_flag_does_not_escalate_further():
    signal = ClassifiedSignal(
        tickers=["AAPL"],
        direction="bullish",
        catalyst_type="earnings",
        magnitude=4,
        confidence=0.8,
        flag_level=FlagLevel.RED,
    )
    signal.escalate()
    assert signal.flag_level == FlagLevel.RED


def test_none_flag_does_not_escalate():
    signal = ClassifiedSignal(
        tickers=["MSFT"],
        direction="bearish",
        catalyst_type="regulatory",
        magnitude=1,
        confidence=0.3,
        flag_level=FlagLevel.NONE,
    )
    signal.escalate()
    assert signal.flag_level == FlagLevel.NONE
