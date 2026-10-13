from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Order, OrderSide, OrderStatus


class OrderRepository:
    """Read-only queries on the order book. Writes live in services/market.py."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _open(self, side: str):
        return select(Order).where(Order.side == side, Order.status == OrderStatus.OPEN)

    async def get(self, order_id: int) -> Order | None:
        stmt = select(Order).where(Order.id == order_id).execution_options(populate_existing=True)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def best_ask(
        self, *, exclude_user_id: int | None = None, max_price: int | None = None
    ) -> Order | None:
        """Cheapest open sell order (oldest first on ties)."""
        stmt = self._open(OrderSide.SELL)
        if exclude_user_id is not None:
            stmt = stmt.where(Order.user_id != exclude_user_id)
        if max_price is not None:
            stmt = stmt.where(Order.price <= max_price)
        stmt = stmt.order_by(Order.price.asc(), Order.id.asc()).limit(1)
        stmt = stmt.execution_options(populate_existing=True)
        return (await self._session.execute(stmt)).scalars().first()

    async def best_bid(
        self, *, exclude_user_id: int | None = None, min_price: int | None = None
    ) -> Order | None:
        """Highest open buy order (oldest first on ties)."""
        stmt = self._open(OrderSide.BUY)
        if exclude_user_id is not None:
            stmt = stmt.where(Order.user_id != exclude_user_id)
        if min_price is not None:
            stmt = stmt.where(Order.price >= min_price)
        stmt = stmt.order_by(Order.price.desc(), Order.id.asc()).limit(1)
        stmt = stmt.execution_options(populate_existing=True)
        return (await self._session.execute(stmt)).scalars().first()

    async def depth(self, side: str, limit: int = 5) -> list[tuple[int, int]]:
        """Top price levels as (price, number_of_orders). Best price first."""
        ordering = Order.price.asc() if side == OrderSide.SELL else Order.price.desc()
        stmt = (
            select(Order.price, func.count())
            .where(Order.side == side, Order.status == OrderStatus.OPEN)
            .group_by(Order.price)
            .order_by(ordering)
            .limit(limit)
        )
        return [(price, count) for price, count in (await self._session.execute(stmt)).all()]

    async def list_open_for_user(self, user_id: int, limit: int = 20) -> list[Order]:
        stmt = (
            select(Order)
            .where(Order.user_id == user_id, Order.status == OrderStatus.OPEN)
            .order_by(Order.id.desc())
            .limit(limit)
            .execution_options(populate_existing=True)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def locked_amount(self, user_id: int) -> int:
        """Money currently reserved by the user's open buy orders."""
        stmt = select(func.coalesce(func.sum(Order.price), 0)).where(
            Order.user_id == user_id,
            Order.side == OrderSide.BUY,
            Order.status == OrderStatus.OPEN,
        )
        return int((await self._session.execute(stmt)).scalar_one())
