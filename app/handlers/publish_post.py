from aiogram import Router
from aiogram.types import CallbackQuery

from app.keyboards.inline.post_this_post import PostThisPostCallback
from app.services.rabbit.pulisher import RabbitMQPublisher

publish_post_router = Router()

@publish_post_router.callback_query(PostThisPostCallback.filter())
async def publish_post(query: CallbackQuery, callback_data: PostThisPostCallback):
    try:
        publisher = RabbitMQPublisher()
        data = {
            'post_id': callback_data.post_id
        }
        await publisher.publish('posts_bot.publish_post', data)
        await query.message.edit_text("Post published!", reply_markup=None)
        await query.answer()
    except Exception as e:
        print(e)
