from typing import Any, List

from aiogram.types import InputMediaPhoto

from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.keyboards.inline.post_this_post import post_this_post_keyboard
from app.main import bot


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
        for post in posts:
            images: List[str] = post.get('images') or []
            text: str = post.get('text') or ''
            keyboard = post_this_post_keyboard(post_id=post.get('post_id'), request_id=self.request_id)
            if images:
                media_group = []
                for i, image_url in enumerate(images):
                    if i == 0:
                        media_group.append(InputMediaPhoto(media=image_url, caption=text, parse_mode="HTML"))
                    else:
                        media_group.append(InputMediaPhoto(media=image_url))
                await bot.send_media_group(chat_id=user.telegram_id, media=media_group)

                await bot.send_message(chat_id=user.telegram_id, text="👆", reply_markup=keyboard)
            elif text:
                await bot.send_message(chat_id=user.telegram_id, text=text, reply_markup=keyboard, parse_mode="HTML")


