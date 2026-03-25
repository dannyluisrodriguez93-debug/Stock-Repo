"""SMS alert channel via Twilio."""

import asyncio

from twilio.rest import Client

from config.settings import get_settings
from layer3_alert.channels.base import AlertChannel
from shared.logging import get_logger

log = get_logger(__name__)


class SMSChannel(AlertChannel):
    def __init__(self) -> None:
        settings = get_settings()
        self._client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self._from = settings.twilio_from_number
        self._to = settings.twilio_to_number
        self._pending: dict[str, bool | None] = {}

    @property
    def name(self) -> str:
        return "sms"

    async def send_alert(self, message: str) -> str:
        # Truncate for SMS
        if len(message) > 1600:
            message = message[:1597] + "..."

        msg = await asyncio.to_thread(
            self._client.messages.create,
            body=message,
            from_=self._from,
            to=self._to,
        )

        log.info("sms_alert_sent", sid=msg.sid)
        return msg.sid

    async def wait_for_response(self, message_id: str, timeout_sec: int) -> bool | None:
        """Poll for incoming SMS reply. Checks for GO/NO keywords."""
        poll_interval = 10
        elapsed = 0

        while elapsed < timeout_sec:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            try:
                messages = await asyncio.to_thread(
                    self._client.messages.list,
                    from_=self._to,
                    to=self._from,
                    limit=5,
                )

                for msg in messages:
                    body = msg.body.strip().upper()
                    if body in ("GO", "YES", "Y"):
                        return True
                    elif body in ("NO", "N", "SKIP"):
                        return False

            except Exception as e:
                log.error("sms_poll_error", error=str(e))

        return None
