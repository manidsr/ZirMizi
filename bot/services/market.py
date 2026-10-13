"""The exchange engine. Every public method is ONE database transaction.

Money safety rules used throughout:
  * Debits are `UPDATE ... WHERE balance >= amount` (can never go negative).
  * Taking an order is `UPDATE ... WHERE status = 'open'` and we check that exactly
    one row changed, so two people can never get the same order.
  * Anything that goes wrong rolls the whole transaction back: no half-trades.

Matching rules (price-time priority, trade at the *resting* order's price):
  * Buy order  matches the cheapest sell order priced <= the bid; the buyer gets
    the difference back.
  * Sell order matches the highest buy order priced >= the ask; the seller gets
    the (better) bid price.
  * Nobody matches their own orders.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import (
    Coupon,
    CouponStatus,
    Order,
    OrderSide,
    OrderStatus,
    Trade,
    TradeKind,
    TxKind,
    User,
    Wallet,
    WalletTransaction,
)
from bot.db.repositories import OrderRepository, WalletRepository
from bot.utils.money import calc_fee

MAX_MATCH_ATTEMPTS = 5


class MarketError(Exception):
    """Base class for expected business-rule failures."""


class InsufficientFunds(MarketError):
    def __init__(self, needed: int) -> None:
        super().__init__(f"needs {needed}")
        self.needed = needed


class OrderUnavailable(MarketError):
    """Order was already filled / cancelled / is your own."""


class DuplicateCoupon(MarketError):
    """This QR code is already in the system."""


@dataclass(frozen=True)
class CouponInfo:
    file_id: str
    file_unique_id: str
    fingerprint: str


@dataclass(frozen=True)
class Fill:
    """A completed trade, with what handlers need to message both sides."""

    trade_id: int
    price: int
    fee: int
    net: int  # what the seller received
    coupon: Coupon
    buyer_tg_id: int
    seller_tg_id: int
    buy_order_id: int | None
    sell_order_id: int | None


@dataclass(frozen=True)
class MatchResult:
    """Either the trade happened right away (`fill`) or an order now rests in the book."""

    fill: Fill | None = None
    order: Order | None = None


@dataclass(frozen=True)
class Cancelled:
    order: Order
    coupon: Coupon | None  # the returned coupon, for sell orders


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _rowcount(result: Any) -> int:
    return getattr(result, "rowcount", 0)


class MarketService:
    def __init__(self, session: AsyncSession, *, fee_bps: int = 0) -> None:
        self._session = session
        self._fee_bps = fee_bps
        self._orders = OrderRepository(session)
        self._wallets = WalletRepository(session)

    # ------------------------------------------------------------------ public

    async def is_coupon_available(self, info: CouponInfo, seller_id: int) -> bool:
        """False if this QR is already in the system (unless it's the seller's own withdrawn one)."""
        existing = await self._find_coupon(info.fingerprint)
        if existing is None:
            return True
        return existing.seller_id == seller_id and existing.status == CouponStatus.WITHDRAWN

    async def instant_buy(self, buyer_id: int, sell_order_id: int) -> Fill:
        """Buy one specific sell order right now at its price."""
        await self._wallets.get_or_create(buyer_id)
        ask = await self._orders.get(sell_order_id)
        if ask is None or ask.side != OrderSide.SELL or ask.user_id == buyer_id:
            raise OrderUnavailable
        price = ask.price

        async with self._transaction():
            await self._debit(buyer_id, price)
            await self._claim(ask.id, OrderSide.SELL, exclude_user_id=buyer_id)
            coupon = await self._coupon_of(ask)
            fill = await self._settle(
                TradeKind.INSTANT_BUY,
                coupon,
                buyer_id=buyer_id,
                seller_id=ask.user_id,
                price=price,
                sell_order_id=ask.id,
            )
            self._ledger(buyer_id, TxKind.PURCHASE, -price, trade_id=fill.trade_id)
        return fill

    async def instant_sell(self, seller_id: int, buy_order_id: int, info: CouponInfo) -> Fill:
        """Sell a coupon right now into one specific buy order, at its price."""
        await self._wallets.get_or_create(seller_id)
        bid = await self._orders.get(buy_order_id)
        if bid is None or bid.side != OrderSide.BUY or bid.user_id == seller_id:
            raise OrderUnavailable

        async with self._transaction():
            coupon = await self._new_coupon(seller_id, info)
            await self._claim(bid.id, OrderSide.BUY, exclude_user_id=seller_id)
            return await self._settle(
                TradeKind.INSTANT_SELL,
                coupon,
                buyer_id=bid.user_id,
                seller_id=seller_id,
                price=bid.price,  # the buyer's money is already reserved
                buy_order_id=bid.id,
            )

    async def place_buy_order(self, buyer_id: int, bid_price: int) -> MatchResult:
        """Reserve `bid_price`, then buy at once if a cheap enough sell order exists."""
        await self._wallets.get_or_create(buyer_id)

        async with self._transaction():
            await self._debit(buyer_id, bid_price)
            lock = self._ledger(buyer_id, TxKind.BUY_LOCK, -bid_price)

            for _ in range(MAX_MATCH_ATTEMPTS):
                ask = await self._orders.best_ask(exclude_user_id=buyer_id, max_price=bid_price)
                if ask is None:
                    break
                if not await self._try_claim(ask.id, OrderSide.SELL, exclude_user_id=buyer_id):
                    continue  # someone beat us to it; look at the next one
                coupon = await self._coupon_of(ask)
                fill = await self._settle(
                    TradeKind.BUY_ORDER,
                    coupon,
                    buyer_id=buyer_id,
                    seller_id=ask.user_id,
                    price=ask.price,
                    sell_order_id=ask.id,
                )
                lock.trade_id = fill.trade_id
                refund = bid_price - ask.price
                if refund:
                    await self._credit(buyer_id, refund)
                    self._ledger(buyer_id, TxKind.REFUND, refund, trade_id=fill.trade_id)
                return MatchResult(fill=fill)

            order = Order(user_id=buyer_id, side=OrderSide.BUY, price=bid_price)
            self._session.add(order)
            await self._session.flush()
            lock.order_id = order.id
            return MatchResult(order=order)

    async def place_sell_order(self, seller_id: int, ask_price: int, info: CouponInfo) -> MatchResult:
        """List a coupon at `ask_price`, or sell at once if a high enough buy order exists."""
        await self._wallets.get_or_create(seller_id)

        async with self._transaction():
            coupon = await self._new_coupon(seller_id, info)

            for _ in range(MAX_MATCH_ATTEMPTS):
                bid = await self._orders.best_bid(exclude_user_id=seller_id, min_price=ask_price)
                if bid is None:
                    break
                if not await self._try_claim(bid.id, OrderSide.BUY, exclude_user_id=seller_id):
                    continue
                fill = await self._settle(
                    TradeKind.SELL_ORDER,
                    coupon,
                    buyer_id=bid.user_id,
                    seller_id=seller_id,
                    price=bid.price,
                    buy_order_id=bid.id,
                )
                return MatchResult(fill=fill)

            order = Order(
                user_id=seller_id, side=OrderSide.SELL, price=ask_price, coupon_id=coupon.id
            )
            self._session.add(order)
            await self._session.flush()
            return MatchResult(order=order)

    async def cancel_order(self, user_id: int, order_id: int) -> Cancelled:
        """Cancel your own open order. Buy: money comes back. Sell: coupon is released."""
        async with self._transaction():
            result = await self._session.execute(
                update(Order)
                .where(Order.id == order_id, Order.user_id == user_id, Order.status == OrderStatus.OPEN)
                .values(status=OrderStatus.CANCELLED, closed_at=_utcnow())
                .execution_options(synchronize_session=False)
            )
            if _rowcount(result) != 1:
                raise OrderUnavailable

            order = await self._orders.get(order_id)
            assert order is not None
            coupon = None
            if order.side == OrderSide.BUY:
                await self._credit(user_id, order.price)
                self._ledger(user_id, TxKind.BUY_UNLOCK, order.price, order_id=order.id)
            else:
                coupon = await self._coupon_of(order)
                coupon.status = CouponStatus.WITHDRAWN
            return Cancelled(order=order, coupon=coupon)

    # ---------------------------------------------------------------- internals

    @asynccontextmanager
    async def _transaction(self) -> AsyncIterator[None]:
        try:
            yield
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def _debit(self, user_id: int, amount: int) -> None:
        result = await self._session.execute(
            update(Wallet)
            .where(Wallet.user_id == user_id, Wallet.balance >= amount)
            .values(balance=Wallet.balance - amount)
            .execution_options(synchronize_session=False)
        )
        if _rowcount(result) != 1:
            raise InsufficientFunds(amount)

    async def _credit(self, user_id: int, amount: int) -> None:
        result = await self._session.execute(
            update(Wallet)
            .where(Wallet.user_id == user_id)
            .values(balance=Wallet.balance + amount)
            .execution_options(synchronize_session=False)
        )
        if _rowcount(result) != 1:  # every order owner got a wallet when they placed it
            raise RuntimeError(f"wallet missing for user {user_id}")

    def _ledger(
        self,
        user_id: int,
        kind: str,
        amount: int,
        *,
        order_id: int | None = None,
        trade_id: int | None = None,
    ) -> WalletTransaction:
        entry = WalletTransaction(
            user_id=user_id, kind=kind, amount=amount, order_id=order_id, trade_id=trade_id
        )
        self._session.add(entry)
        return entry

    async def _try_claim(self, order_id: int, side: str, *, exclude_user_id: int) -> bool:
        """Atomically flip an open order to filled. True only for the one caller that wins."""
        result = await self._session.execute(
            update(Order)
            .where(
                Order.id == order_id,
                Order.side == side,
                Order.status == OrderStatus.OPEN,
                Order.user_id != exclude_user_id,
            )
            .values(status=OrderStatus.FILLED, closed_at=_utcnow())
            .execution_options(synchronize_session=False)
        )
        return _rowcount(result) == 1

    async def _claim(self, order_id: int, side: str, *, exclude_user_id: int) -> None:
        if not await self._try_claim(order_id, side, exclude_user_id=exclude_user_id):
            raise OrderUnavailable

    async def _coupon_of(self, order: Order) -> Coupon:
        coupon = await self._session.get(Coupon, order.coupon_id)
        if coupon is None:
            raise RuntimeError(f"sell order {order.id} has no coupon")
        return coupon

    async def _find_coupon(self, fingerprint: str) -> Coupon | None:
        stmt = select(Coupon).where(Coupon.fingerprint == fingerprint)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def _new_coupon(self, seller_id: int, info: CouponInfo) -> Coupon:
        existing = await self._find_coupon(info.fingerprint)
        if existing is not None:
            if existing.seller_id == seller_id and existing.status == CouponStatus.WITHDRAWN:
                existing.status = CouponStatus.LISTED  # relisting something you pulled back
                existing.file_id = info.file_id
                existing.file_unique_id = info.file_unique_id
                return existing
            raise DuplicateCoupon

        coupon = Coupon(
            seller_id=seller_id,
            file_id=info.file_id,
            file_unique_id=info.file_unique_id,
            fingerprint=info.fingerprint,
        )
        self._session.add(coupon)
        try:
            await self._session.flush()
        except IntegrityError:
            raise DuplicateCoupon from None
        return coupon

    async def _settle(
        self,
        kind: str,
        coupon: Coupon,
        *,
        buyer_id: int,
        seller_id: int,
        price: int,
        buy_order_id: int | None = None,
        sell_order_id: int | None = None,
    ) -> Fill:
        """Pay the seller, hand over the coupon, record the trade."""
        fee = calc_fee(price, self._fee_bps)
        net = price - fee
        await self._credit(seller_id, net)

        coupon.status = CouponStatus.SOLD
        coupon.buyer_id = buyer_id
        trade = Trade(
            kind=kind,
            coupon_id=coupon.id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            price=price,
            fee=fee,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
        )
        self._session.add(trade)
        await self._session.flush()
        self._ledger(seller_id, TxKind.SALE, net, order_id=sell_order_id, trade_id=trade.id)

        buyer = await self._session.get(User, buyer_id)
        seller = await self._session.get(User, seller_id)
        assert buyer is not None and seller is not None
        return Fill(
            trade_id=trade.id,
            price=price,
            fee=fee,
            net=net,
            coupon=coupon,
            buyer_tg_id=buyer.telegram_id,
            seller_tg_id=seller.telegram_id,
            buy_order_id=buy_order_id,
            sell_order_id=sell_order_id,
        )
