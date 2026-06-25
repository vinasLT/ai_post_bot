import base64
from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile

from app.core.logger import logger
from app.core.bot import bot
from app.services.post_generation.user_facing_errors import format_telegram_error
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.services.forum_publish_service import ForumPublishService
from app.services.process_posts.post_process_service import PostProcessService


class PostDeliveryService:
    """Delivers post-generation results directly to Telegram (replaces posts_service.* Rabbit routes)."""

    @staticmethod
    async def send_generated_posts(payload: dict[str, Any]) -> None:
        await PostProcessService(payload).process_posts()

    @staticmethod
    async def send_manually_generated_post(payload: dict[str, Any]) -> None:
        await PostProcessService(payload).process_posts()

    @staticmethod
    async def update_message(message_id: int, text: str, user_uuid: str) -> None:
        try:
            async with get_db() as db:
                user_service = UserService(db)
                user = await user_service.get_by_uuid(user_uuid)
            if user is None:
                return
            await bot.edit_message_text(
                text=text,
                chat_id=user.telegram_id,
                message_id=message_id,
                parse_mode=None,
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e).lower():
                return
            logger.warning(f"Error while updating message: {e}")
        except Exception as e:
            logger.warning(f"Error while updating message: {e}")

    @staticmethod
    async def send_image_generated(payload: dict[str, Any]) -> None:
        image: str = payload["image"]
        message_id: int = payload["message_id"]
        user_uuid: str = payload["user_uuid"]
        image_bytes = base64.b64decode(image)

        async with get_db() as db:
            user_service = UserService(db)
            user = await user_service.get_by_uuid(user_uuid)
        if user is None:
            return

        try:
            await bot.delete_message(chat_id=user.telegram_id, message_id=message_id)
        except TelegramBadRequest:
            pass

        photo = BufferedInputFile(image_bytes, "image.png")
        await bot.send_photo(chat_id=user.telegram_id, photo=photo)

    @staticmethod
    async def publish_to_forum(payload: dict[str, Any]) -> None:
        await ForumPublishService().publish(payload)

    @staticmethod
    async def send_error(user_uuid: str, error_message: str, request_id: int | None) -> None:
        async with get_db() as db:
            user_service = UserService(db)
            user = await user_service.get_by_uuid(user_uuid)
        if user is None:
            logger.error("posts_service.error: user not found", extra={"user_uuid": user_uuid})
            return
        text = format_telegram_error(error_message, request_id)
        await bot.send_message(chat_id=user.telegram_id, text=text, parse_mode=None)
