"""Screens shared by the menu buttons and the inline buttons (text + keyboard)."""

from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import OrderSide
from bot.db.repositories import OrderRepository
from bot.keyboards.market import buy_kb, my_orders_kb, sell_kb
from bot.texts import t
from bot.utils.money import format_amount


def _depth_text(rows: list[tuple[int, int]]) -> str:
    if not rows:
        return t("market_none")
    return "\n".join(t("depth_row", price=format_amount(p), count=c) for p, c in rows)


async def buy_screen(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
    rows = await OrderRepository(session).depth(OrderSide.SELL)
    best = f"{format_amount(rows[0][0])} تومان" if rows else t("market_none")
    return t("buy_screen", best=best, depth=_depth_text(rows)), buy_kb()


async def sell_screen(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
    rows = await OrderRepository(session).depth(OrderSide.BUY)
    best = f"{format_amount(rows[0][0])} تومان" if rows else t("market_none")
    return t("sell_screen", best=best, depth=_depth_text(rows)), sell_kb()


async def my_orders_screen(
    session: AsyncSession, user_id: int
) -> tuple[str, InlineKeyboardMarkup | None]:
    orders = await OrderRepository(session).list_open_for_user(user_id)
    if not orders:
        return t("my_orders_empty"), None
    rows = "\n".join(
        t(
            "my_orders_row",
            id=o.id,
            side=t("side_buy") if o.side == OrderSide.BUY else t("side_sell"),
            price=format_amount(o.price),
        )
        for o in orders
    )
    return t("my_orders_title", rows=rows), my_orders_kb([o.id for o in orders])
