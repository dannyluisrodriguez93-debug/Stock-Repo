"""Abstract broker adapter."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from layer4_execution.models import Order, OrderSide


class BrokerAdapter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def submit_order(
        self, ticker: str, side: OrderSide, quantity: int, limit_price: float | None = None
    ) -> Order:
        ...

    @abstractmethod
    async def get_position(self, ticker: str) -> dict | None:
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        ...

    @abstractmethod
    async def get_account_info(self) -> dict:
        ...

    @abstractmethod
    async def stream_price(self, ticker: str) -> AsyncIterator[float]:
        ...
