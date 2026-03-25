"""Discord webhook alert channel."""

import asyncio

import aiohttp

from config.settings import get_settings
from layer3_alert.channels.base import AlertChannel
from shared.logging import get_logger

log = get_logger(__name__)


class DiscordChannel(AlertChannel):
    def __init__(self) -> None:
        settings = get_settings()
        self._webhook_url = settings.discord_webhook_url

    @property
    def name(self) -> str:
        return "discord"

    async def send_alert(self, message: str) -> str:
        payload = {"content": f"```\n{message}\n```"}

        async with aiohttp.ClientSession() as session:
            async with session.post(self._webhook_url, json=payload) as resp:
                if resp.status in (200, 204):
                    log.info("discord_alert_sent")
                    return "discord_msg"
                else:
                    text = await resp.text()
                    log.error("discord_send_error", status=resp.status, body=text)
                    return ""

    async def wait_for_response(self, message_id: str, timeout_sec: int) -> bool | None:
        """Discord webhooks are one-way; fall back to timeout-based approval."""
        log.warning("discord_no_response", msg="Discord webhook cannot receive responses; timing out")
        await asyncio.sleep(timeout_sec)
        return None
