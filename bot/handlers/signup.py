from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User
from bot.db.repositories import UserRepository
from bot.keyboards.main_menu import main_menu_kb
from bot.keyboards.signup import SIGNUP_START
from bot.texts import t

router = Router(name="signup")

MAX_NAME_LENGTH = 64


class SignupStates(StatesGroup):
    first_name = State()
    last_name = State()


def clean_name(raw: str | None) -> str | None:
    """Return a tidy name, or None if the input isn't acceptable."""
    if raw is None:
        return None
    name = " ".join(raw.split())
    if not name or len(name) > MAX_NAME_LENGTH or name.startswith("/"):
        return None
    return name


@router.callback_query(F.data == SIGNUP_START)
async def signup_start(callback: CallbackQuery, state: FSMContext, user: User | None) -> None:
    await callback.answer()
    message = callback.message
    if not isinstance(message, Message):
        return

    if user is not None:
        await message.answer(t("already_registered"), reply_markup=main_menu_kb())
        return

    await state.set_state(SignupStates.first_name)
    await message.answer(t("ask_first_name"))


@router.message(SignupStates.first_name)
async def got_first_name(message: Message, state: FSMContext) -> None:
    first_name = clean_name(message.text)
    if first_name is None:
        await message.answer(t("invalid_name"))
        return

    await state.update_data(first_name=first_name)
    await state.set_state(SignupStates.last_name)
    await message.answer(t("ask_last_name"))


@router.message(SignupStates.last_name)
async def got_last_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    last_name = clean_name(message.text)
    if last_name is None:
        await message.answer(t("invalid_name"))
        return

    data = await state.get_data()
    first_name = data.get("first_name")
    tg_user = message.from_user
    if first_name is None or tg_user is None:
        await state.clear()
        await message.answer(t("start_over"))
        return

    await UserRepository(session).create(
        telegram_id=tg_user.id,
        first_name=first_name,
        last_name=last_name,
        username=tg_user.username,
    )
    await state.clear()
    await message.answer(
        t("signup_done", name=escape(first_name)),
        reply_markup=main_menu_kb(),
    )
