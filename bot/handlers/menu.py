from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.handlers.market_views import buy_screen, my_orders_screen, sell_screen
from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.texts import t

router = Router(name="menu")
# Everything in this router is for signed-up users only.
router.message.middleware(RequireRegisteredMiddleware())

# Wallet and Account have their own routers: handlers/wallet.py, handlers/account.py.
# The buy/sell *flows* (buttons under the screens) live in handlers/market.py.
# Pressing any menu button also cancels a half-finished flow (state.clear()).


@router.message(F.text == t("btn_buy_food"))
async def buy_food(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    text, keyboard = await buy_screen(session)
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == t("btn_sell_food"))
async def sell_food(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    text, keyboard = await sell_screen(session)
    await message.answer(text, reply_markup=keyboard)


@router.message(F.text == t("btn_my_orders"))
async def my_orders(message: Message, state: FSMContext, user: User, session: AsyncSession) -> None:
    await state.clear()
    text, keyboard = await my_orders_screen(session, user.id)
    await message.answer(text, reply_markup=keyboard)
