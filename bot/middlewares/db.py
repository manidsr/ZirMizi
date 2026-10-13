from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.db.repositories import UserRepository


class DbSessionMiddleware(BaseMiddleware):
    """Gives every handler a DB session and the current user.

    Handlers can simply declare `session: AsyncSession` and/or
    `user: User | None` (None means the person hasn't signed up yet).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self._session_factory() as session:
            data["session"] = session
            tg_user = data.get("event_from_user")
            data["user"] = (
                await UserRepository(session).get_by_telegram_id(tg_user.id) if tg_user else None
            )
            return await handler(event, data)
