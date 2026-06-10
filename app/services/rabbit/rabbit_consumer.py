import base64
import json
from enum import Enum

from aio_pika.abc import AbstractIncomingMessage
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BufferedInputFile

from app.core.logger import logger
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.main import bot
from app.services.forum_publish_service import ForumPublishService
from app.services.process_posts.post_process_service import PostProcessService
from app.services.rabbit.consumer_base import RabbitBaseService

class PostsBotRoutingKeys(str, Enum):
    POSTS_SERVICE_GENERATED_POSTS = "posts_service.generated_posts"
    POSTS_SERVICE_PUBLISH_POST = 'posts_service.publish_post'
    POSTS_SERVICE_ERROR = 'posts_service.error'
    POSTS_SERVICE_MANUALLY_GENERATED_POST = 'posts_service.manually_generated_post'
    POSTS_SERVICE_UPDATE_MESSAGE = 'posts_service.update_message'
    POSTS_SERVICE_IMAGE_GENERATED = 'posts_service.image_generated'


class RabbitPostsBotConsumer(RabbitBaseService):
    async def process_message(self, message: AbstractIncomingMessage):
        message_data = message.body.decode("utf-8")
        payload = json.loads(message_data).get("payload")
        routing_key = message.routing_key
        logger.info(f"Received new message", extra={"message_data": message_data})

        if routing_key in PostsBotRoutingKeys:
            route = PostsBotRoutingKeys(routing_key)
        else:
            return

        if route in [PostsBotRoutingKeys.POSTS_SERVICE_GENERATED_POSTS, PostsBotRoutingKeys.POSTS_SERVICE_MANUALLY_GENERATED_POST] :
            posts_service = PostProcessService(payload)
            await posts_service.process_posts()
        elif route == PostsBotRoutingKeys.POSTS_SERVICE_UPDATE_MESSAGE:
            try:
                async with get_db() as db:
                    user_service = UserService(db)
                    user = await user_service.get_by_uuid(payload.get('user_uuid'))
                # Disable bot default Markdown — progress text can contain _, etc.
                await bot.edit_message_text(
                    text=payload.get('message'),
                    chat_id=user.telegram_id,
                    message_id=payload.get('message_id'),
                    parse_mode=None,
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e).lower():
                    return
                logger.warning(f"Error while updating message: {e}")
            except Exception as e:
                logger.warning(f"Error while updating message: {e}")
        elif route == PostsBotRoutingKeys.POSTS_SERVICE_IMAGE_GENERATED:
            image: bytes = payload["image"]
            message_id: int = payload["message_id"]
            user_uuid: str = payload["user_uuid"]
            image_bytes = base64.b64decode(image)

            async with get_db() as db:
                user_service = UserService(db)
                user = await user_service.get_by_uuid(user_uuid)

            try:
                await bot.delete_message(chat_id=user.telegram_id, message_id=message_id)
            except TelegramBadRequest:
                pass

            photo = BufferedInputFile(image_bytes, "image.png")
            await bot.send_photo(chat_id=user.telegram_id, photo=photo)


        elif route == PostsBotRoutingKeys.POSTS_SERVICE_PUBLISH_POST:
            await ForumPublishService().publish(payload)
        elif route == PostsBotRoutingKeys.POSTS_SERVICE_ERROR:
            async with get_db() as db:
                user_service = UserService(db)
                user = await user_service.get_by_uuid(payload.get('user_uuid'))
            if user is None:
                logger.error(
                    "posts_service.error: user not found",
                    extra={"user_uuid": payload.get('user_uuid')},
                )
                return
            error = payload.get('error_message') or ''
            request_id = payload.get('request_id')
            # LLM/runtime errors may contain em dashes, <>&, etc. Telegram HTML still rejects some
            # valid-looking payloads ("can't parse entities"); plain text always delivers.
            text = (
                "❌ An error occurred while processing your request:\n"
                f"Message: {error}\n"
                f"Request ID: {request_id}\n"
            )
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode=None,
            )






