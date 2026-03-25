"""Tests for Layer 4 execution models."""

from datetime import datetime

from layer4_execution.models import (
    ExitTrigger,
    ExecutionResult,
    Order,
    OrderSide,
    OrderStatus,
    Position,
)


def test_order_creation():
    order = Order(
        order_id="abc123",
        ticker="AAPL",
        side=OrderSide.BUY,
        quantity=10,
        price=165.0,
        status=OrderStatus.FILLED,
    )
    assert order.side == OrderSide.BUY
    assert order.quantity == 10


def test_position_creation():
    pos = Position(
        ticker="BA",
        direction="bullish",
        quantity=50,
        entry_price=162.0,
        target_price=175.0,
        stop_loss=155.0,
        catalyst_type="contract_win",
    )
    assert pos.ticker == "BA"
    assert pos.quantity == 50


def test_execution_result_pnl():
    result = ExecutionResult(
        ticker="BA",
        entry_price=162.0,
        exit_price=175.0,
        exit_trigger=ExitTrigger.TAKE_PROFIT,
        quantity=50,
        pnl=650.0,
        pnl_pct=8.02,
        held_duration_sec=7200,
    )
    assert result.pnl > 0
    assert result.exit_trigger == ExitTrigger.TAKE_PROFIT


def test_exit_triggers():
    assert ExitTrigger.TAKE_PROFIT.value == "take_profit"
    assert ExitTrigger.TRAILING_STOP.value == "trailing_stop"
    assert ExitTrigger.TIME_DECAY.value == "time_decay"
    assert ExitTrigger.VOLUME_DIVERGENCE.value == "volume_divergence"
