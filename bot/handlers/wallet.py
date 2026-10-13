from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.db.repositories import WalletRepository
from bot.keyboards.wallet import WALLET_DEPOSIT, WALLET_TRANSFER, WALLET_WITHDRAW, wallet_kb
from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.texts import t
from bot.utils.money import format_amount

router = Router(name="wallet")
router.message.middleware(RequireRegisteredMiddleware())
router.callback_query.middleware(RequireRegisteredMiddleware())


@router.message(F.text == t("btn_wallet"))
async def show_wallet(message: Message, state: FSMContext, user: User, session: AsyncSession) -> None:
    await state.clear()
    wallet = await WalletRepository(session).get_or_create(user.id)
    await message.answer(
        t("wallet_balance", balance=format_amount(wallet.balance)),
        reply_markup=wallet_kb(),
    )


@router.callback_query(F.data.in_({WALLET_WITHDRAW, WALLET_DEPOSIT, WALLET_TRANSFER}))
async def wallet_action(callback: CallbackQuery) -> None:
    # Placeholder until withdraw / deposit / transfer are implemented.
    await callback.answer(t("coming_soon"), show_alert=True)
