from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.texts import t


class RequireRegisteredMiddleware(BaseMiddleware):
    """Blocks a router's handlers for people who haven't signed up."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if data.get("user") is None:
            if isinstance(event, Message):
                await event.answer(t("not_registered"))
            elif isinstance(event, CallbackQuery):
                await event.answer(t("not_registered"), show_alert=True)
            return None
        return await handler(event, data)
