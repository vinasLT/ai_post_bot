from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.keyboards.inline.main_menu import MainMenuActions, MainMenuCallback


class PostThisPostCallback(CallbackData, prefix="main_menu"):
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
    builder.adjust(1)
    return builder.as_markup()
