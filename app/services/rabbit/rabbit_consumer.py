import json
from enum import Enum

from aio_pika.abc import AbstractIncomingMessage
from aiogram.types import InputMediaPhoto

from app.config import settings
from app.core.logger import logger
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.main import bot
from app.services.process_posts.post_process_service import PostProcessService
from app.services.rabbit.consumer_base import RabbitBaseService

class PostsBotRoutingKeys(str, Enum):
    POSTS_SERVICE_GENERATED_POSTS = "posts_service.generated_posts"
    POSTS_SERVICE_PUBLISH_POST = 'posts_service.publish_post'
    POSTS_SERVICE_ERROR = 'posts_service.error'
    POSTS_SERVICE_MANUALLY_GENERATED_POST = 'posts_service.manually_generated_post'
    POSTS_SERVICE_UPDATE_MESSAGE = 'posts_service.update_message'


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
                await bot.edit_message_text(
                    text=payload.get('message'),
                    chat_id=user.telegram_id,
                    message_id=payload.get('message_id')
                )
            except Exception as e:
                logger.warning(f"Error while updating message: {e}")
        elif route == PostsBotRoutingKeys.POSTS_SERVICE_PUBLISH_POST:
            text = payload.get('text')
            images = payload.get('images')
            media = []
            for i, url in enumerate(images[:5]):
                if i == 0:
                    media.append(InputMediaPhoto(media=url, caption=text, parse_mode="HTML"))
                else:
                    media.append(InputMediaPhoto(media=url))
            await bot.send_media_group(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                media=media
            )
        elif route == PostsBotRoutingKeys.POSTS_SERVICE_ERROR:
            async with get_db() as db:
                user_service = UserService(db)
                user = await user_service.get_by_uuid(payload.get('user_uuid'))
            error = payload.get('error_message')
            request_id = payload.get('request_id')

            text = (f"❌ An error occurred while processing your request:\n"
                    f"Message: {error}\n"
                    f"Request ID: {request_id}\n")
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text
            )






