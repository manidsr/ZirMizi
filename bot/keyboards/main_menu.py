from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.texts import t


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Main menu, 2 buttons per row. Add new buttons here later."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_buy_food")), KeyboardButton(text=t("btn_sell_food"))],
            [KeyboardButton(text=t("btn_wallet")), KeyboardButton(text=t("btn_account"))],
            [KeyboardButton(text=t("btn_my_orders"))],
        ],
        resize_keyboard=True,
    )
