from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


class UserRepository:
    """All database access for users lives here, not in handlers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self._session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        telegram_id: int,
        first_name: str,
        last_name: str,
        username: str | None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        self._session.add(user)
        try:
            await self._session.commit()
        except IntegrityError:
            # Same person finished signup twice at once: keep the first record.
            await self._session.rollback()
            existing = await self.get_by_telegram_id(telegram_id)
            if existing is None:
                raise
            return existing
        return user
