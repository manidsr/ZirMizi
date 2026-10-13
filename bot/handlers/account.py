from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import BankAccount, User
from bot.db.repositories import BankAccountRepository
from bot.handlers.signup import clean_name
from bot.keyboards.account import BANK_CANCEL, BANK_EDIT, account_kb, bank_cancel_kb
from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.texts import t
from bot.utils.cards import mask_card, parse_card_number
from bot.utils.names import names_match

router = Router(name="account")
router.message.middleware(RequireRegisteredMiddleware())
router.callback_query.middleware(RequireRegisteredMiddleware())


class BankStates(StatesGroup):
    card_number = State()
    card_holder = State()


def _account_text(user: User, bank: BankAccount | None) -> str:
    if bank is None:
        bank_info = t("bank_not_set")
    else:
        bank_info = t(
            "bank_info",
            card=mask_card(bank.card_number),
            holder=escape(bank.card_holder_name),
        )
    return t(
        "account_info",
        first_name=escape(user.first_name),
        last_name=escape(user.last_name),
        bank_info=bank_info,
    )


@router.message(F.text == t("btn_account"))
async def show_account(message: Message, state: FSMContext, user: User, session: AsyncSession) -> None:
    await state.clear()
    bank = await BankAccountRepository(session).get_by_user_id(user.id)
    await message.answer(_account_text(user, bank), reply_markup=account_kb(has_bank=bank is not None))


@router.callback_query(F.data == BANK_EDIT)
async def bank_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    message = callback.message
    if not isinstance(message, Message):
        return
    await state.set_state(BankStates.card_number)
    await message.answer(t("bank_intro"))
    await message.answer(t("ask_card_number"), reply_markup=bank_cancel_kb())


@router.callback_query(F.data == BANK_CANCEL)
async def bank_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    if isinstance(callback.message, Message):
        await callback.message.answer(t("bank_cancelled"))


@router.message(BankStates.card_number)
async def got_card_number(message: Message, state: FSMContext) -> None:
    card_number = parse_card_number(message.text)
    if card_number is None:
        await message.answer(t("invalid_card_number"), reply_markup=bank_cancel_kb())
        return

    await state.update_data(card_number=card_number)
    await state.set_state(BankStates.card_holder)
    await message.answer(t("ask_card_holder"), reply_markup=bank_cancel_kb())


@router.message(BankStates.card_holder)
async def got_card_holder(message: Message, state: FSMContext, user: User, session: AsyncSession) -> None:
    holder = clean_name(message.text)
    if holder is None:
        await message.answer(t("invalid_name"), reply_markup=bank_cancel_kb())
        return

    data = await state.get_data()
    card_number = data.get("card_number")
    if card_number is None:
        await state.clear()
        await message.answer(t("start_over"))
        return

    # Read what we need from `user` before touching the DB.
    user_id, first_name, last_name = user.id, user.first_name, user.last_name

    await BankAccountRepository(session).upsert(
        user_id=user_id,
        card_number=card_number,
        card_holder_name=holder,
    )
    await state.clear()

    text = t("bank_saved")
    if not names_match(holder, first_name, last_name):
        # We still save it (the field is optional and the signup name may be
        # wrong), but the user is told withdrawals need a matching name.
        text += "\n\n" + t(
            "bank_name_mismatch",
            first_name=escape(first_name),
            last_name=escape(last_name),
        )
    await message.answer(text)
