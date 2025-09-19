from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.database.models import FilterPreset


class PresetCallback(CallbackData, prefix="preset"):
    action: str
    preset_name: str | None = None
    preset_id: int | None = None

class PresetsActions:
    SAVE_PRESET = "save_preset"
    LOAD_PRESET = "load_preset"
    OPEN_PRESET = "open_preset"
    GET_ALL_PRESETS = "get_all_presets"
    DELETE_PRESET = "delete_preset"

def open_preset_keyboard(presets: list[FilterPreset]):
    builder = InlineKeyboardBuilder()
    for preset in presets:
        builder.button(text=preset.name, callback_data=PresetCallback(action=PresetsActions.OPEN_PRESET, preset_name=preset.name, preset_id=preset.id).pack())
    builder.adjust(1)
    return builder.as_markup()
def load_or_delete_preset_keyboard(preset_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Load", callback_data=PresetCallback(action=PresetsActions.LOAD_PRESET,  preset_id=preset_id).pack())
    builder.button(text="🗑 Delete", callback_data=PresetCallback(action=PresetsActions.DELETE_PRESET, preset_id=preset_id).pack())
    builder.adjust(2)
    return builder.as_markup()


