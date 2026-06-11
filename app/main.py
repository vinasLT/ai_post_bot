import asyncio
from typing import Any, Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject
from aiogram import BaseMiddleware

from app.config import settings
from app.core.logger import intercept_stdlib_logging, logger
from app.handlers.generate_invite_code import invite_code_router
from app.handlers.generate_post_manually import generate_post_manually_router
from app.handlers.generate_posts_with_filters import generate_posts_with_filters_router
from app.handlers.presets import presets_router
from app.handlers.publish_post import publish_post_router
from app.handlers.start import start_router


class UpdateLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = getattr(event, "from_user", None)
        logger.info(
            "Incoming update",
            update_type=type(event).__name__,
            user_id=getattr(from_user, "id", None),
            username=getattr(from_user, "username", None),
        )
        try:
            return await handler(event, data)
        except Exception:
            logger.exception(
                "Handler failed",
                update_type=type(event).__name__,
                user_id=getattr(from_user, "id", None),
            )
            raise


bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))


async def main():
    intercept_stdlib_logging()
    bot_user = await bot.get_me()
    logger.info(
        "Starting Telegram bot",
        bot_username=bot_user.username,
        bot_id=bot_user.id,
        environment=settings.ENVIRONMENT.value,
        debug=settings.DEBUG,
        db_backend="sqlite" if settings.use_sqlite_db else "postgresql",
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.middleware(UpdateLoggingMiddleware())

    dp.include_routers(start_router)
    dp.include_router(invite_code_router)
    dp.include_router(generate_posts_with_filters_router)
    dp.include_router(presets_router)
    dp.include_router(publish_post_router)
    dp.include_router(generate_post_manually_router)

    logger.info("Polling started")
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())