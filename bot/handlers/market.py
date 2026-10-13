"""Buy / sell flows: instant buy, instant sell, buy order, sell order, cancel."""

import asyncio
import logging
from hashlib import sha256
from io import BytesIO

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.db.models import OrderSide, User
from bot.db.repositories import OrderRepository, WalletRepository
from bot.handlers.market_views import my_orders_screen
from bot.keyboards.market import (
    MKT_BUY_ORDER,
    MKT_CANCEL_FLOW,
    MKT_CANCEL_ORDER,
    MKT_INSTANT_BUY,
    MKT_INSTANT_BUY_OK,
    MKT_INSTANT_SELL,
    MKT_INSTANT_SELL_OK,
    MKT_MY_ORDERS,
    MKT_SELL_ORDER,
    confirm_kb,
    flow_cancel_kb,
)
from bot.middlewares.registered import RequireRegisteredMiddleware
from bot.services.market import (
    CouponInfo,
    DuplicateCoupon,
    Fill,
    InsufficientFunds,
    MarketService,
    OrderUnavailable,
)
from bot.texts import t
from bot.utils.money import calc_fee, format_amount, parse_amount
from bot.utils.qr import QR_SUPPORTED, decode_qr

logger = logging.getLogger(__name__)

router = Router(name="market")
router.message.middleware(RequireRegisteredMiddleware())
router.callback_query.middleware(RequireRegisteredMiddleware())


class BuyOrderStates(StatesGroup):
    price = State()


class InstantSellStates(StatesGroup):
    photo = State()
    confirm = State()


class SellOrderStates(StatesGroup):
    photo = State()
    price = State()


# ----------------------------------------------------------------- helpers


def _service(session: AsyncSession) -> MarketService:
    return MarketService(session, fee_bps=get_settings().fee_bps)


def _fmt(amount: int) -> str:
    return format_amount(amount)


def _message(callback: CallbackQuery) -> Message | None:
    return callback.message if isinstance(callback.message, Message) else None


def _parse_id(data: str | None, prefix: str) -> int | None:
    if data is None:
        return None
    raw = data.removeprefix(prefix)
    return int(raw) if raw.isdigit() else None


async def _drop_keyboard(callback: CallbackQuery) -> None:
    """Remove the buttons so a double tap can't fire the action twice."""
    message = _message(callback)
    if message is None:
        return
    try:
        await message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass


async def _safe_send(bot: Bot, chat_id: int, text: str, photo: str | None = None) -> None:
    """Notify the other side of a trade. They may have blocked the bot: never crash on that."""
    try:
        if photo:
            await bot.send_photo(chat_id, photo, caption=text)
        else:
            await bot.send_message(chat_id, text)
    except TelegramAPIError:
        logger.warning("Could not notify chat %s", chat_id, exc_info=True)


def _fee_line(fee: int) -> str:
    return t("fee_line", fee=_fmt(fee)) if fee else ""


async def _notify_seller(bot: Bot, fill: Fill) -> None:
    """Tell the seller whose resting sell order was just filled."""
    text = t(
        "sell_filled_notify",
        order_id=fill.sell_order_id,
        price=_fmt(fill.price),
        fee_line=_fee_line(fill.fee),
        net=_fmt(fill.net),
    )
    await _safe_send(bot, fill.seller_tg_id, text)


async def _notify_buyer(bot: Bot, fill: Fill) -> None:
    """Deliver the QR to the buyer whose resting buy order was just filled."""
    text = t("buy_filled_notify", order_id=fill.buy_order_id, price=_fmt(fill.price))
    await _safe_send(bot, fill.buyer_tg_id, text, photo=fill.coupon.file_id)


async def _insufficient(session: AsyncSession, user_id: int, needed: int) -> str:
    balance = await WalletRepository(session).balance(user_id)
    return t("insufficient_funds", balance=_fmt(balance), needed=_fmt(needed))


def _price_in_range(price: int | None) -> bool:
    settings = get_settings()
    return price is not None and settings.min_price <= price <= settings.max_price


def _invalid_price_text() -> str:
    settings = get_settings()
    return t("invalid_price", min=_fmt(settings.min_price), max=_fmt(settings.max_price))


async def _read_coupon(
    message: Message, bot: Bot, service: MarketService, user_id: int
) -> CouponInfo | None:
    """Validate the uploaded photo and turn it into a CouponInfo. Replies on failure."""
    if not message.photo:
        await message.answer(t("not_a_photo"), reply_markup=flow_cancel_kb())
        return None

    photo = message.photo[-1]  # largest size
    payload: str | None = None
    if get_settings().qr_check and QR_SUPPORTED:
        buffer = await bot.download(photo, destination=BytesIO())
        payload = await asyncio.to_thread(decode_qr, buffer.getvalue()) if buffer else None
        if payload is None:
            await message.answer(t("qr_unreadable"), reply_markup=flow_cancel_kb())
            return None

    fingerprint = sha256(payload.encode()).hexdigest() if payload else photo.file_unique_id
    info = CouponInfo(file_id=photo.file_id, file_unique_id=photo.file_unique_id, fingerprint=fingerprint)
    if not await service.is_coupon_available(info, user_id):
        await message.answer(t("coupon_duplicate"), reply_markup=flow_cancel_kb())
        return None
    return info


def _coupon_from_state(data: dict) -> CouponInfo | None:
    try:
        return CouponInfo(data["file_id"], data["file_unique_id"], data["fingerprint"])
    except KeyError:
        return None


# ------------------------------------------------------------ common buttons


@router.callback_query(F.data == MKT_CANCEL_FLOW)
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await _drop_keyboard(callback)
    if message := _message(callback):
        await message.answer(t("cancelled"))


@router.callback_query(F.data == MKT_MY_ORDERS)
async def show_my_orders(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession) -> None:
    await callback.answer()
    await state.clear()
    if message := _message(callback):
        text, keyboard = await my_orders_screen(session, user.id)
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(MKT_CANCEL_ORDER))
async def cancel_order(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    await callback.answer()
    message = _message(callback)
    order_id = _parse_id(callback.data, MKT_CANCEL_ORDER)
    if message is None or order_id is None:
        return
    try:
        result = await _service(session).cancel_order(user.id, order_id)
    except OrderUnavailable:
        await message.answer(t("order_unavailable"))
        return

    if result.order.side == OrderSide.BUY:
        await message.answer(
            t("order_cancelled_buy", id=order_id, price=_fmt(result.order.price))
        )
    elif result.coupon is not None:
        await message.answer_photo(result.coupon.file_id, caption=t("order_cancelled_sell", id=order_id))
    # Refresh the list so the cancelled order's button disappears.
    text, keyboard = await my_orders_screen(session, user.id)
    await message.answer(text, reply_markup=keyboard)


# --------------------------------------------------------------- instant buy


@router.callback_query(F.data == MKT_INSTANT_BUY)
async def instant_buy_start(callback: CallbackQuery, user: User, session: AsyncSession) -> None:
    await callback.answer()
    message = _message(callback)
    if message is None:
        return
    ask = await OrderRepository(session).best_ask(exclude_user_id=user.id)
    if ask is None:
        await message.answer(t("no_ask"))
        return
    balance = await WalletRepository(session).balance(user.id)
    if balance < ask.price:
        await message.answer(t("insufficient_funds", balance=_fmt(balance), needed=_fmt(ask.price)))
        return
    await message.answer(
        t("confirm_instant_buy", price=_fmt(ask.price), balance=_fmt(balance)),
        reply_markup=confirm_kb(f"{MKT_INSTANT_BUY_OK}{ask.id}"),
    )


@router.callback_query(F.data.startswith(MKT_INSTANT_BUY_OK))
async def instant_buy_confirm(callback: CallbackQuery, user: User, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    message = _message(callback)
    order_id = _parse_id(callback.data, MKT_INSTANT_BUY_OK)
    if message is None or order_id is None:
        return
    await _drop_keyboard(callback)

    try:
        fill = await _service(session).instant_buy(user.id, order_id)
    except InsufficientFunds as exc:
        await message.answer(await _insufficient(session, user.id, exc.needed))
        return
    except OrderUnavailable:
        await message.answer(t("order_unavailable"))
        return

    await message.answer_photo(fill.coupon.file_id, caption=t("instant_buy_done", price=_fmt(fill.price)))
    await _notify_seller(bot, fill)


# ---------------------------------------------------------------- buy order


@router.callback_query(F.data == MKT_BUY_ORDER)
async def buy_order_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    message = _message(callback)
    if message is None:
        return
    settings = get_settings()
    await state.set_state(BuyOrderStates.price)
    await message.answer(
        t("ask_buy_price", min=_fmt(settings.min_price), max=_fmt(settings.max_price)),
        reply_markup=flow_cancel_kb(),
    )


@router.message(BuyOrderStates.price)
async def got_buy_price(
    message: Message, state: FSMContext, user: User, session: AsyncSession, bot: Bot
) -> None:
    price = parse_amount(message.text)
    if price is None or not _price_in_range(price):
        await message.answer(_invalid_price_text(), reply_markup=flow_cancel_kb())
        return

    try:
        result = await _service(session).place_buy_order(user.id, price)
    except InsufficientFunds as exc:
        # Stay in the flow so they can type a lower price.
        await message.answer(await _insufficient(session, user.id, exc.needed), reply_markup=flow_cancel_kb())
        return

    await state.clear()
    if result.fill is not None:
        refund = price - result.fill.price
        await message.answer_photo(
            result.fill.coupon.file_id,
            caption=t(
                "buy_order_filled_now",
                price=_fmt(result.fill.price),
                refund_line=t("refund_line", refund=_fmt(refund)) if refund else "",
            ),
        )
        await _notify_seller(bot, result.fill)
    elif result.order is not None:
        await message.answer(t("buy_order_placed", id=result.order.id, price=_fmt(price)))


# -------------------------------------------------------------- instant sell


@router.callback_query(F.data == MKT_INSTANT_SELL)
async def instant_sell_start(
    callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession
) -> None:
    await callback.answer()
    message = _message(callback)
    if message is None:
        return
    bid = await OrderRepository(session).best_bid(exclude_user_id=user.id)
    if bid is None:
        await message.answer(t("no_bid"))
        return
    await state.set_state(InstantSellStates.photo)
    await message.answer(
        t("ask_instant_sell_photo", price=_fmt(bid.price), ask_photo=t("ask_sell_photo")),
        reply_markup=flow_cancel_kb(),
    )


@router.message(InstantSellStates.photo, F.photo)
async def got_instant_sell_photo(
    message: Message, state: FSMContext, user: User, session: AsyncSession, bot: Bot
) -> None:
    service = _service(session)
    info = await _read_coupon(message, bot, service, user.id)
    if info is None:
        return

    # Re-quote now: the best bid may have changed while they were taking the photo.
    bid = await OrderRepository(session).best_bid(exclude_user_id=user.id)
    if bid is None:
        await state.clear()
        await message.answer(t("no_bid"))
        return

    await state.update_data(
        file_id=info.file_id, file_unique_id=info.file_unique_id, fingerprint=info.fingerprint
    )
    await state.set_state(InstantSellStates.confirm)
    fee = calc_fee(bid.price, get_settings().fee_bps)
    await message.answer(
        t(
            "confirm_instant_sell",
            price=_fmt(bid.price),
            fee_line=_fee_line(fee),
            net=_fmt(bid.price - fee),
        ),
        reply_markup=confirm_kb(f"{MKT_INSTANT_SELL_OK}{bid.id}"),
    )


@router.callback_query(InstantSellStates.confirm, F.data.startswith(MKT_INSTANT_SELL_OK))
async def instant_sell_confirm(
    callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession, bot: Bot
) -> None:
    await callback.answer()
    message = _message(callback)
    bid_id = _parse_id(callback.data, MKT_INSTANT_SELL_OK)
    info = _coupon_from_state(await state.get_data())
    if message is None:
        return
    await _drop_keyboard(callback)
    if bid_id is None or info is None:
        await state.clear()
        await message.answer(t("start_over"))
        return

    try:
        fill = await _service(session).instant_sell(user.id, bid_id, info)
    except OrderUnavailable:
        await state.clear()
        await message.answer(t("order_unavailable"))
        return
    except DuplicateCoupon:
        await state.clear()
        await message.answer(t("coupon_duplicate"))
        return

    await state.clear()
    await message.answer(t("instant_sell_done", net=_fmt(fill.net)))
    await _notify_buyer(bot, fill)


# --------------------------------------------------------------- sell order


@router.callback_query(F.data == MKT_SELL_ORDER)
async def sell_order_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    message = _message(callback)
    if message is None:
        return
    await state.set_state(SellOrderStates.photo)
    await message.answer(t("ask_sell_photo"), reply_markup=flow_cancel_kb())


@router.message(SellOrderStates.photo, F.photo)
async def got_sell_photo(
    message: Message, state: FSMContext, user: User, session: AsyncSession, bot: Bot
) -> None:
    info = await _read_coupon(message, bot, _service(session), user.id)
    if info is None:
        return
    settings = get_settings()
    await state.update_data(
        file_id=info.file_id, file_unique_id=info.file_unique_id, fingerprint=info.fingerprint
    )
    await state.set_state(SellOrderStates.price)
    await message.answer(
        t("ask_sell_price", min=_fmt(settings.min_price), max=_fmt(settings.max_price)),
        reply_markup=flow_cancel_kb(),
    )


@router.message(SellOrderStates.price)
async def got_sell_price(
    message: Message, state: FSMContext, user: User, session: AsyncSession, bot: Bot
) -> None:
    price = parse_amount(message.text)
    if price is None or not _price_in_range(price):
        await message.answer(_invalid_price_text(), reply_markup=flow_cancel_kb())
        return

    info = _coupon_from_state(await state.get_data())
    if info is None:
        await state.clear()
        await message.answer(t("start_over"))
        return

    try:
        result = await _service(session).place_sell_order(user.id, price, info)
    except DuplicateCoupon:
        await state.clear()
        await message.answer(t("coupon_duplicate"))
        return

    await state.clear()
    if result.fill is not None:
        await message.answer(
            t(
                "sell_order_filled_now",
                price=_fmt(result.fill.price),
                fee_line=_fee_line(result.fill.fee),
                net=_fmt(result.fill.net),
            )
        )
        await _notify_buyer(bot, result.fill)
    elif result.order is not None:
        await message.answer(t("sell_order_placed", id=result.order.id, price=_fmt(price)))


# Must stay LAST among the photo handlers: catches anything that isn't a photo
# while we are waiting for one (the photo handlers above match first).
@router.message(InstantSellStates.photo)
@router.message(SellOrderStates.photo)
async def photo_expected(message: Message) -> None:
    await message.answer(t("not_a_photo"), reply_markup=flow_cancel_kb())
