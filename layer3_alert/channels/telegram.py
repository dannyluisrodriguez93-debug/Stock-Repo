"""Telegram alert channel with inline keyboard approval."""

import asyncio

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler

from config.settings import get_settings
from layer3_alert.channels.base import AlertChannel
from shared.logging import get_logger

log = get_logger(__name__)


class TelegramChannel(AlertChannel):
    def __init__(self) -> None:
        settings = get_settings()
        self._bot_token = settings.telegram_bot_token
        self._chat_id = settings.telegram_chat_id
        self._bot: Bot | None = None
        self._pending_responses: dict[str, asyncio.Future] = {}
        self._app: Application | None = None

    @property
    def name(self) -> str:
        return "telegram"

    def _get_bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(token=self._bot_token)
        return self._bot

    async def _start_listener(self) -> None:
        """Start listening for callback button presses."""
        if self._app is not None:
            return

        self._app = Application.builder().token(self._bot_token).build()
        self._app.add_handler(CallbackQueryHandler(self._handle_callback))
        await self._app.initialize()
        await self._app.start()
        await self._app.updater.start_polling()
        log.info("telegram_listener_started")

    async def _handle_callback(self, update: Update, context) -> None:
        """Handle inline keyboard button press."""
        query = update.callback_query
        await query.answer()

        msg_id = str(query.message.message_id)
        approved = query.data == "go"

        if msg_id in self._pending_responses:
            self._pending_responses[msg_id].set_result(approved)
            status = "APPROVED" if approved else "REJECTED"
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"Trade {status}")
            log.info("telegram_response", message_id=msg_id, approved=approved)

    async def send_alert(self, message: str) -> str:
        bot = self._get_bot()
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("GO", callback_data="go"),
                InlineKeyboardButton("NO", callback_data="no"),
            ]
        ])

        msg = await bot.send_message(
            chat_id=self._chat_id,
            text=message,
            reply_markup=keyboard,
            parse_mode=None,
        )

        msg_id = str(msg.message_id)
        log.info("telegram_alert_sent", message_id=msg_id)
        return msg_id

    async def wait_for_response(self, message_id: str, timeout_sec: int) -> bool | None:
        await self._start_listener()

        future = asyncio.get_event_loop().create_future()
        self._pending_responses[message_id] = future

        try:
            result = await asyncio.wait_for(future, timeout=timeout_sec)
            return result
        except asyncio.TimeoutError:
            log.warning("telegram_timeout", message_id=message_id)
            return None
        finally:
            self._pending_responses.pop(message_id, None)

    async def shutdown(self) -> None:
        if self._app:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
