from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import t

WALLET_WITHDRAW = "wallet:withdraw"
WALLET_DEPOSIT = "wallet:deposit"
WALLET_TRANSFER = "wallet:transfer"


def wallet_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_withdraw"), callback_data=WALLET_WITHDRAW),
                InlineKeyboardButton(text=t("btn_deposit"), callback_data=WALLET_DEPOSIT),
                InlineKeyboardButton(text=t("btn_transfer"), callback_data=WALLET_TRANSFER),
            ]
        ]
    )
