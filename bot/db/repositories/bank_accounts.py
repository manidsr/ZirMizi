from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import BankAccount


class BankAccountRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: int) -> BankAccount | None:
        result = await self._session.execute(
            select(BankAccount).where(BankAccount.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: int,
        card_number: str,
        card_holder_name: str,
    ) -> BankAccount:
        """Create the user's bank info, or replace it if it already exists."""
        account = await self.get_by_user_id(user_id)
        if account is None:
            account = BankAccount(
                user_id=user_id,
                card_number=card_number,
                card_holder_name=card_holder_name,
            )
            self._session.add(account)
        else:
            account.card_number = card_number
            account.card_holder_name = card_holder_name
        await self._session.commit()
        return account
