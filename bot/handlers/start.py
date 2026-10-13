from html import escape

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.db.models import User
from bot.keyboards.main_menu import main_menu_kb
from bot.keyboards.signup import signup_kb
from bot.texts import t

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User | None) -> None:
    # /start always resets any half-finished signup.
    await state.clear()

    if user is not None:
        await message.answer(
            t("welcome_back", name=escape(user.first_name)),
            reply_markup=main_menu_kb(),
        )
        return

    tg_user = message.from_user
    name = escape(tg_user.full_name) if tg_user else t("default_name")
    await message.answer(t("welcome", name=name), reply_markup=signup_kb())
