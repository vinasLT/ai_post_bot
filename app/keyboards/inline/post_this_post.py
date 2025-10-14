from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.inline.main_menu import MainMenuActions, MainMenuCallback


class PostThisPostCallback(CallbackData, prefix='post_this_post'):
    add_comment: bool = False
    post_id: int
    request_id: int

class GeneratePostImageCallback(CallbackData, prefix="generate_post_image"):
    post_id: int
    request_id: int

def post_this_post_keyboard(post_id: int, request_id: int, is_manual_generation: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Publicate",
                   callback_data=PostThisPostCallback(post_id=post_id, request_id=request_id).pack())
    builder.button(text='🗃 Open Filters',
                   callback_data=MainMenuCallback(action=MainMenuActions.GENERATE_POST_WITH_FILTERS_IN_NEW_MESSAGE).pack())
    if is_manual_generation:
        builder.button(text='📄 Generate Next Lot Manually', callback_data=MainMenuCallback(action=MainMenuActions.GENERATE_POST_MANUALLY).pack())
        builder.button(text='💬 Add Comment', callback_data=PostThisPostCallback(post_id=post_id, request_id=request_id, add_comment=True).pack())
        builder.button(text='🖼 Generate Image', callback_data=GeneratePostImageCallback(post_id=post_id, request_id=request_id).pack())
    builder.adjust(1)
    return builder.as_markup()
