"""Abstract base for alert channels."""

from abc import ABC, abstractmethod


class AlertChannel(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def send_alert(self, message: str) -> str:
        """Send alert message. Returns a message ID for tracking."""
        ...

    @abstractmethod
    async def wait_for_response(self, message_id: str, timeout_sec: int) -> bool | None:
        """Wait for go/no-go response. Returns True=go, False=no, None=timeout."""
        ...
