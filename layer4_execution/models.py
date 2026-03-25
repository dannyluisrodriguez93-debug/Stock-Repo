"""Data models for Layer 4 - Execution + Position Monitoring."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class ExitTrigger(str, Enum):
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_DECAY = "time_decay"
    VOLUME_DIVERGENCE = "volume_divergence"
    MANUAL = "manual"


class Order(BaseModel):
    order_id: str = ""
    ticker: str
    side: OrderSide
    quantity: int
    price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    filled_price: float = 0.0
    filled_at: datetime | None = None


class Position(BaseModel):
    ticker: str
    direction: str
    quantity: int
    entry_price: float
    target_price: float
    stop_loss: float
    catalyst_type: str
    opened_at: datetime = Field(default_factory=datetime.utcnow)
    high_water_mark: float = 0.0
    current_price: float = 0.0


class ExecutionResult(BaseModel):
    ticker: str
    entry_price: float
    exit_price: float
    exit_trigger: ExitTrigger
    quantity: int
    pnl: float
    pnl_pct: float
    held_duration_sec: float
