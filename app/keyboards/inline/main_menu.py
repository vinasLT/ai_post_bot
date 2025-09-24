from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class MainMenuActions(str, Enum):
    GENERATE_POST_WITH_FILTERS = "generate_with_filters"
    GENERATE_POST_WITH_FILTERS_IN_NEW_MESSAGE = 'generate_with_filters_in_new_message'
    GENERATE_POST = "generate_plain"

class MainMenuCallback(CallbackData, prefix="main_menu"):
    action: str

def main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Generate Post With AI ✨",
                   callback_data=MainMenuCallback(action=MainMenuActions.GENERATE_POST_WITH_FILTERS).pack())
    builder.button(text="Generate Post Manually (will be available soon)", callback_data=MainMenuCallback(action=MainMenuActions.GENERATE_POST).pack())
    builder.adjust(1)
    return builder.as_markup()
