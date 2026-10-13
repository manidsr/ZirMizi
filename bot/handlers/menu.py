from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.texts import t

router = Router(name="menu")
# Everything in this router is for signed-up users only.
router.message.middleware(RequireRegisteredMiddleware())

# Wallet and Account have their own routers: handlers/wallet.py, handlers/account.py.
# Pressing any menu button also cancels a half-finished flow (state.clear()).


@router.message(F.text == t("btn_buy_food"))
async def buy_food(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("coming_soon"))


@router.message(F.text == t("btn_sell_food"))
async def sell_food(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(t("coming_soon"))
