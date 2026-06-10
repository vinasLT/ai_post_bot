"""Reply in each forum topic with its message_thread_id (for TELEGRAM_TOPIC_IDS_JSON setup)."""

import asyncio

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import settings
from app.core.logger import intercept_stdlib_logging, logger

router = Router()
FORUM_CHAT_ID = str(settings.TELEGRAM_FORUM_CHAT_ID)


@router.message(Command("thread_id"))
async def thread_id_command(message: Message) -> None:
    if str(message.chat.id) != FORUM_CHAT_ID:
        return
    thread_id = message.message_thread_id
    if thread_id is None:
        await message.reply("General topic — no message_thread_id (not a forum topic thread).")
        return
    await message.reply(
        f"message_thread_id for this topic: <code>{thread_id}</code>\n"
        f"Add to TELEGRAM_TOPIC_IDS_JSON when you map this language.",
        parse_mode="HTML",
    )
    logger.info(
        "Thread ID reported",
        extra={"message_thread_id": thread_id, "chat_id": message.chat.id},
    )


@router.message()
async def any_forum_message(message: Message) -> None:
    if str(message.chat.id) != FORUM_CHAT_ID:
        return
    thread_id = message.message_thread_id
    if thread_id is None:
        return
    if message.text and message.text.startswith("/"):
        return
    await message.reply(
        f"This topic's message_thread_id: <code>{thread_id}</code>",
        parse_mode="HTML",
    )
    logger.info(
        "Thread ID reported",
        extra={"message_thread_id": thread_id, "chat_id": message.chat.id},
    )


async def main() -> None:
    intercept_stdlib_logging()
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    me = await bot.get_me()
    logger.info(
        "Thread ID discovery bot started",
        extra={
            "bot_username": me.username,
            "forum_chat_id": FORUM_CHAT_ID,
            "hint": "Send any message in each forum topic, or /thread_id",
        },
    )
    print(f"Bot @{me.username} listening on forum {FORUM_CHAT_ID}")
    print("Post in each language topic — bot will reply with message_thread_id.")
    print("Or send /thread_id inside a topic. Ctrl+C to stop.")

    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
