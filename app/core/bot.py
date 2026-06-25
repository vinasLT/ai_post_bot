from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import settings
from app.core.telegram_retry_middleware import RetryAfterMiddleware

bot = Bot(
    token=settings.TELEGRAM_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
)
bot.session.middleware.register(
    RetryAfterMiddleware(max_retries=settings.TELEGRAM_RETRY_AFTER_MAX_RETRIES)
)
