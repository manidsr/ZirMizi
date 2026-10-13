import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import get_settings
from bot.db.session import create_engine, create_session_factory, init_db
from bot.handlers import get_root_router
from bot.logging_setup import setup_logging
from bot.middlewares.db import DbSessionMiddleware

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # FSM state is kept in memory for now (lost on restart).
    # Switch to RedisStorage when you run more than one instance.
    dp = Dispatcher()
    dp.update.outer_middleware(DbSessionMiddleware(session_factory))
    dp.include_router(get_root_router())

    try:
        await init_db(engine)
        me = await bot.get_me()
        logger.info("Starting bot @%s", me.username)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await engine.dispose()
