from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Wallet


class WalletRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _get(self, user_id: int) -> Wallet | None:
        result = await self._session.execute(select(Wallet).where(Wallet.user_id == user_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: int) -> Wallet:
        """Return the user's wallet, creating it with a 0 balance if missing.

        Creating lazily also covers users who signed up before wallets existed.
        """
        wallet = await self._get(user_id)
        if wallet is not None:
            return wallet

        wallet = Wallet(user_id=user_id, balance=0)
        self._session.add(wallet)
        try:
            await self._session.commit()
        except IntegrityError:
            # Two requests created it at the same moment: use the first one.
            await self._session.rollback()
            existing = await self._get(user_id)
            if existing is None:
                raise
            return existing
        return wallet
