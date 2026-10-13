from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.db.models import TxKind
from bot.db.repositories import UserRepository, WalletRepository
from bot.texts import t
from bot.utils.money import format_amount, parse_amount

router = Router(name="admin")


@router.message(Command("credit"))
async def credit(message: Message, command: CommandObject, session: AsyncSession) -> None:
    """/credit <telegram_id> <amount>: add Toman to a user's wallet (admins only).

    Stand-in for real deposits until the payment gateway exists.
    """
    if message.from_user is None or message.from_user.id not in get_settings().admin_ids:
        return  # silently ignore everyone else

    parts = (command.args or "").split()
    amount = parse_amount(parts[1]) if len(parts) == 2 else None
    if len(parts) != 2 or not parts[0].isdigit() or not amount:
        await message.answer(t("admin_credit_usage"))
        return

    target = await UserRepository(session).get_by_telegram_id(int(parts[0]))
    if target is None:
        await message.answer(t("admin_user_not_found"))
        return

    balance = await WalletRepository(session).credit(target.id, amount, TxKind.ADMIN_CREDIT)
    await message.answer(
        t("admin_credit_ok", amount=format_amount(amount), tg_id=parts[0], balance=format_amount(balance))
    )
