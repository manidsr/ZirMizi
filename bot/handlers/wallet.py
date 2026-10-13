from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.db.repositories import OrderRepository, WalletRepository
from bot.keyboards.wallet import WALLET_DEPOSIT, WALLET_TRANSFER, WALLET_WITHDRAW, wallet_kb
from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.texts import t
from bot.utils.money import format_amount

# TESTING ONLY: what the deposit button adds.
TEST_DEPOSIT_AMOUNT = 100_000
TEST_DEPOSIT_KIND = "test_deposit"

router = Router(name="wallet")
router.message.middleware(RequireRegisteredMiddleware())
router.callback_query.middleware(RequireRegisteredMiddleware())


@router.message(F.text == t("btn_wallet"))
async def show_wallet(message: Message, state: FSMContext, user: User, session: AsyncSession) -> None:
    await state.clear()
    wallet = await WalletRepository(session).get_or_create(user.id)
    locked = await OrderRepository(session).locked_amount(user.id)
    await message.answer(
        t("wallet_balance", balance=format_amount(wallet.balance), locked=format_amount(locked)),
        reply_markup=wallet_kb(),
    )


@router.callback_query(F.data == WALLET_DEPOSIT)
async def wallet_deposit(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    """TESTING ONLY: adds a fixed amount instead of a real payment.

    Replace with the payment gateway flow before going live.
    """
    wallets = WalletRepository(session)
    balance = await wallets.credit(user.id, TEST_DEPOSIT_AMOUNT, TEST_DEPOSIT_KIND)
    await callback.answer(t("test_deposit_done", amount=format_amount(TEST_DEPOSIT_AMOUNT)), show_alert=True)

    # Refresh the wallet message with the new balance.
    if isinstance(callback.message, Message):
        locked = await OrderRepository(session).locked_amount(user.id)
        try:
            await callback.message.edit_text(
                t("wallet_balance", balance=format_amount(balance), locked=format_amount(locked)),
                reply_markup=wallet_kb(),
            )
        except TelegramBadRequest:
            pass


@router.callback_query(F.data.in_({WALLET_WITHDRAW, WALLET_TRANSFER}))
async def wallet_action(callback: CallbackQuery) -> None:
    # Placeholder until withdraw / transfer are implemented.
    await callback.answer(t("coming_soon"), show_alert=True)
