from datetime import datetime, timezone

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- string constants (plain strings are portable across SQLite / PostgreSQL) ---
class OrderSide:
    BUY = "buy"
    SELL = "sell"


class OrderStatus:
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"


class CouponStatus:
    LISTED = "listed"  # sitting in a sell order
    SOLD = "sold"
    WITHDRAWN = "withdrawn"  # sell order cancelled, seller got it back


class TradeKind:
    """What the person who triggered the trade (the taker) did."""

    INSTANT_BUY = "instant_buy"
    INSTANT_SELL = "instant_sell"
    BUY_ORDER = "buy_order"
    SELL_ORDER = "sell_order"


class TxKind:
    ADMIN_CREDIT = "admin_credit"
    BUY_LOCK = "buy_lock"  # money reserved for a buy order
    BUY_UNLOCK = "buy_unlock"  # buy order cancelled, money returned
    PURCHASE = "purchase"  # instant buy
    REFUND = "refund"  # buy order filled cheaper than the bid
    SALE = "sale"  # seller receives money (after fee)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64))
    username: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Wallet(Base):
    """One wallet per user. `balance` is the *spendable* amount in whole Toman.

    Money reserved by open buy orders is NOT in `balance`: it is taken out when
    the order is placed and given back if the order is cancelled.
    """

    __tablename__ = "wallets"
    __table_args__ = (CheckConstraint("balance >= 0", name="ck_wallets_balance_non_negative"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class BankAccount(Base):
    """Optional payout details, only needed when the user withdraws money."""

    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    card_number: Mapped[str] = mapped_column(String(16))
    card_holder_name: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Coupon(Base):
    """The thing being traded: one photo containing a food QR code."""

    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    buyer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    file_id: Mapped[str] = mapped_column(String(256))  # Telegram file_id, re-sendable by this bot
    file_unique_id: Mapped[str] = mapped_column(String(64))
    # sha256 of the decoded QR text (or file_unique_id if QR decoding is off).
    # Unique, so the same code can't be sold twice.
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(12), default=CouponStatus.LISTED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Order(Base):
    """A resting order in the book. Instant buy/sell never create one.

    BUY  order: `price` Toman is reserved from the buyer's balance.
    SELL order: `coupon_id` points at the coupon being offered.
    """

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("price > 0", name="ck_orders_price_positive"),
        Index("ix_orders_book", "side", "status", "price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    side: Mapped[str] = mapped_column(String(4))
    price: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(12), default=OrderStatus.OPEN)
    coupon_id: Mapped[int | None] = mapped_column(ForeignKey("coupons.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Trade(Base):
    """History of every completed exchange."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"))
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    price: Mapped[int] = mapped_column(BigInteger)
    fee: Mapped[int] = mapped_column(BigInteger, default=0)
    buy_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), default=None)
    sell_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class WalletTransaction(Base):
    """Ledger: every change to a wallet balance, signed."""

    __tablename__ = "wallet_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[int] = mapped_column(BigInteger)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), default=None)
    trade_id: Mapped[int | None] = mapped_column(ForeignKey("trades.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
