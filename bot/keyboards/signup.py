from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import t

SIGNUP_START = "signup:start"


def signup_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_signup"), callback_data=SIGNUP_START)]]
    )
