from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.database.models.generation_job import GenerationJobType
from app.keyboards.inline.main_menu import main_menu_keyboard
from app.keyboards.inline.post_this_post import PostThisPostCallback
from app.services.post_generation.job_service import enqueue_generation_job

publish_post_router = Router()

@publish_post_router.callback_query(PostThisPostCallback.filter(F.add_comment == False))
async def publish_post(query: CallbackQuery, callback_data: PostThisPostCallback):
    try:
        async with get_db() as db:
            user_service = UserService(db)
            user = await user_service.get_by_telegram_id(str(query.from_user.id))
        if user is None:
            await query.answer("User not found", show_alert=True)
            return
        data = {
            'post_id': callback_data.post_id
        }
        await enqueue_generation_job(GenerationJobType.PUBLISH_POST, data, user.user_uuid)
        await query.message.edit_text(
            "Publishing to forum topics…",
            reply_markup=main_menu_keyboard(),
        )
        await query.answer()
    except Exception as e:
        print(e)
