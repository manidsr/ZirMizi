from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.texts import t

MKT_INSTANT_BUY = "mkt:ib"
MKT_INSTANT_BUY_OK = "mkt:ibok:"  # + sell order id
MKT_BUY_ORDER = "mkt:bo"
MKT_INSTANT_SELL = "mkt:is"
MKT_INSTANT_SELL_OK = "mkt:isok:"  # + buy order id
MKT_SELL_ORDER = "mkt:so"
MKT_MY_ORDERS = "mkt:my"
MKT_CANCEL_ORDER = "mkt:cx:"  # + order id
MKT_CANCEL_FLOW = "mkt:cancel"


def _btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


def buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(t("btn_instant_buy"), MKT_INSTANT_BUY), _btn(t("btn_buy_order"), MKT_BUY_ORDER)],
            [_btn(t("btn_my_orders"), MKT_MY_ORDERS)],
        ]
    )


def sell_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(t("btn_instant_sell"), MKT_INSTANT_SELL), _btn(t("btn_sell_order"), MKT_SELL_ORDER)],
            [_btn(t("btn_my_orders"), MKT_MY_ORDERS)],
        ]
    )


def flow_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[_btn(t("btn_cancel"), MKT_CANCEL_FLOW)]])


def confirm_kb(ok_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[_btn(t("btn_confirm"), ok_data), _btn(t("btn_cancel"), MKT_CANCEL_FLOW)]]
    )


def my_orders_kb(order_ids: list[int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_btn(t("btn_cancel_order", id=order_id), f"{MKT_CANCEL_ORDER}{order_id}")]
            for order_id in order_ids
        ]
    )
