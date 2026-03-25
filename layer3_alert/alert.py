"""Layer 3 - Alert formatting, sending, and approval waiting."""

from config.settings import get_settings
from layer2_deepdive.models import TradeSetup
from layer3_alert.channels.base import AlertChannel
from layer3_alert.channels.discord import DiscordChannel
from layer3_alert.channels.sms import SMSChannel
from layer3_alert.channels.telegram import TelegramChannel
from layer3_alert.models import AlertPayload, ApprovalResponse
from shared.db import Database
from shared.event_bus import ALERT_TO_EXECUTION, DEEPDIVE_TO_ALERT, EventBus
from shared.exceptions import AlertError, ApprovalTimeoutError
from shared.logging import get_logger

log = get_logger(__name__)


def _create_channel(name: str) -> AlertChannel:
    channels = {
        "telegram": TelegramChannel,
        "sms": SMSChannel,
        "discord": DiscordChannel,
    }
    if name not in channels:
        raise AlertError(f"Unknown alert channel: {name}")
    return channels[name]()


class AlertManager:
    """Sends trade alerts and waits for Danny's approval."""

    def __init__(self, event_bus: EventBus, db: Database) -> None:
        self._event_bus = event_bus
        self._db = db
        self._settings = get_settings().alert
        self._primary = _create_channel(self._settings.primary_channel)
        self._fallback = _create_channel(self._settings.fallback_channel)
        self._running = False

    async def _send_and_wait(self, setup: TradeSetup) -> bool:
        """Send alert via primary channel, fall back if needed."""
        payload = AlertPayload.from_trade_setup(setup)
        message = payload.format_message()

        # Try primary channel
        try:
            msg_id = await self._primary.send_alert(message)
            response = await self._primary.wait_for_response(
                msg_id, self._settings.approval_timeout_sec
            )

            if response is not None:
                await self._db.insert_alert(
                    channel=self._primary.name,
                    message=message[:500],
                    approved=int(response),
                )
                return response

            log.warning("primary_channel_timeout", channel=self._primary.name)

        except Exception as e:
            log.error("primary_channel_error", channel=self._primary.name, error=str(e))

        # Fall back
        try:
            log.info("trying_fallback", channel=self._fallback.name)
            msg_id = await self._fallback.send_alert(message)
            response = await self._fallback.wait_for_response(
                msg_id, self._settings.approval_timeout_sec
            )

            if response is not None:
                await self._db.insert_alert(
                    channel=self._fallback.name,
                    message=message[:500],
                    approved=int(response),
                )
                return response

        except Exception as e:
            log.error("fallback_channel_error", channel=self._fallback.name, error=str(e))

        raise ApprovalTimeoutError("No response received on any channel")

    async def run(self) -> None:
        """Main alert consumer loop."""
        self._running = True
        log.info("alert_manager_started")

        while self._running:
            try:
                setup: TradeSetup = await self._event_bus.subscribe(DEEPDIVE_TO_ALERT)

                log.info("alert_processing", ticker=setup.ticker, entry=setup.entry_price)

                approved = await self._send_and_wait(setup)

                if approved:
                    log.info("trade_approved", ticker=setup.ticker)
                    response = ApprovalResponse(approved=True, setup=setup)
                    await self._event_bus.publish(ALERT_TO_EXECUTION, response)
                else:
                    log.info("trade_rejected", ticker=setup.ticker)

            except ApprovalTimeoutError:
                log.warning("approval_timeout", msg="Skipping trade, resuming scanner")
            except Exception as e:
                log.error("alert_error", error=str(e))

    def stop(self) -> None:
        self._running = False
