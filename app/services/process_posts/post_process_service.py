import asyncio
from typing import Any, List

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaPhoto

from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.keyboards.inline.post_this_post import post_this_post_keyboard
from app.core.bot import bot


class PostProcessService:
    def __init__(self, payload: dict[str, Any], ):
        self.payload = payload
        self.user_uuid = payload.get("user_uuid")
        self.request_id = payload.get("request_id")

    async def get_user(self):
        async with get_db() as db:
            user_service = UserService(db)
            user = await user_service.get_by_uuid(self.payload.get("user_uuid"))
            return user

    async def process_posts(self):
        user = await self.get_user()
        if not user:
            return
        posts = self.payload.get('posts') or []
        message_id = self.payload.get('message_id')
        for post in posts:
            images: List[str] = post.get('images') or []
            text: str = post.get('text') or ''
            keyboard = post_this_post_keyboard(post_id=post.get('post_id'), request_id=self.request_id,
                                               is_manual_generation=message_id is not None)
            if images:
                media_group = []
                for i, image_url in enumerate(images):
                    if i == 0:
                        media_group.append(InputMediaPhoto(media=image_url, caption=text, parse_mode="HTML"))
                    else:
                        media_group.append(InputMediaPhoto(media=image_url))
                if message_id:
                    try:
                        await asyncio.sleep(1)
                        await bot.delete_message(chat_id=user.telegram_id, message_id=message_id)
                    except Exception:
                        pass
                await asyncio.sleep(1)
                await bot.send_media_group(chat_id=user.telegram_id, media=media_group)
                await asyncio.sleep(1)
                await bot.send_message(chat_id=user.telegram_id, text="👆", reply_markup=keyboard)
            elif text:
                if message_id:
                    try:
                        await asyncio.sleep(1)
                        await bot.edit_message_text(chat_id=user.telegram_id, message_id=message_id, text=text,
                                                    parse_mode="HTML", reply_markup=keyboard)
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e).lower():
                            pass
                        else:
                            raise
                else:
                    await asyncio.sleep(1)
                    await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=keyboard,
                                           parse_mode="HTML")


