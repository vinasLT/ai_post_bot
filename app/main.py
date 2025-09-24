import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import settings
from app.handlers.generate_invite_code import invite_code_router
from app.handlers.generate_posts_with_filters import generate_posts_with_filters_router
from app.handlers.presets import presets_router
from app.handlers.publish_post import publish_post_router
from app.handlers.start import start_router



bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))

async def main():
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)


    dp.include_routers(start_router)
    dp.include_router(invite_code_router)
    dp.include_router(generate_posts_with_filters_router)
    dp.include_router(presets_router)
    dp.include_router(publish_post_router)

    await dp.start_polling(bot, skip_updates=True)


if __name__ == '__main__':
    print('project starts')
    asyncio.run(main())