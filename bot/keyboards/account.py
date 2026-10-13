from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import t

BANK_EDIT = "bank:edit"
BANK_CANCEL = "bank:cancel"


def account_kb(has_bank: bool) -> InlineKeyboardMarkup:
    text = t("btn_bank_edit") if has_bank else t("btn_bank_add")
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=BANK_EDIT)]])


def bank_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t("btn_cancel"), callback_data=BANK_CANCEL)]]
    )
