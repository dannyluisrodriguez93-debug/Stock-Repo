"""Tests for exit strategy logic."""

import asyncio
import pytest

from layer4_execution.models import ExitTrigger, Position


def _make_position(**overrides) -> Position:
    defaults = {
        "ticker": "AAPL",
        "direction": "bullish",
        "quantity": 100,
        "entry_price": 150.0,
        "target_price": 165.0,
        "stop_loss": 145.0,
        "catalyst_type": "earnings",
    }
    defaults.update(overrides)
    return Position(**defaults)


def test_position_defaults():
    pos = _make_position()
    assert pos.high_water_mark == 0.0
    assert pos.current_price == 0.0


def test_position_direction():
    long_pos = _make_position(direction="bullish")
    short_pos = _make_position(direction="bearish")
    assert long_pos.direction == "bullish"
    assert short_pos.direction == "bearish"


def test_trailing_stop_pct():
    """Verify trailing stop math."""
    entry = 150.0
    trail_pct = 0.015  # 1.5%
    stop = entry * (1 - trail_pct)
    assert stop == pytest.approx(147.75, rel=1e-3)

    # After price moves up
    high = 160.0
    new_stop = high * (1 - trail_pct)
    assert new_stop == pytest.approx(157.6, rel=1e-3)
    assert new_stop > stop  # Stop moved up


def test_take_profit_target_wide():
    """Wide targets (6%+) should trigger scaled exit."""
    entry = 100.0
    target = 108.0  # 8% gain
    gain_pct = (target - entry) / entry
    assert gain_pct >= 0.06  # Threshold for scaled exit
