from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.database.crud.filters_preset import FilterPresetService
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.database.schemas.filter_preset import FilterPresetRead
from app.keyboards.inline.post_generator_filters import create_main_filters_keyboard
from app.keyboards.inline.presets import PresetsActions, PresetCallback, open_preset_keyboard, \
    load_or_delete_preset_keyboard
from app.states.filter_states import FilterStates

presets_router = Router()

@presets_router.callback_query(PresetCallback.filter(F.action == PresetsActions.GET_ALL_PRESETS))
async def load_preset(query: CallbackQuery, state: FSMContext):
    async with get_db() as db:
        user_service = UserService(db)
        preset_filters_service = FilterPresetService(db)

        user = await user_service.get_by_telegram_id(str(query.from_user.id))

        presets = await preset_filters_service.get_presets_for_user(user.id)

        serialized_presets = [FilterPresetRead.model_validate(preset).model_dump(mode='json') for preset in presets]
        await state.update_data(presets=serialized_presets)

        await query.message.edit_text(f'📄 *Presets*\n'
                                      f'- Choose preset to load or delete', reply_markup=open_preset_keyboard(presets))

@presets_router.callback_query(PresetCallback.filter(F.action == PresetsActions.OPEN_PRESET))
async def open_preset(query: CallbackQuery, callback_data: PresetCallback, state: FSMContext):
    async with get_db() as db:
        preset_filters_service = FilterPresetService(db)
        preset = await preset_filters_service.get(callback_data.preset_id)
    if preset:
        await state.update_data(filters=preset)

        await query.message.edit_text(f'📄 Chosen preset: *{preset.name}*\n\n'
                                      f'- Select action below:'
                                      , reply_markup=load_or_delete_preset_keyboard(preset.id))

@presets_router.callback_query(PresetCallback.filter(F.action == PresetsActions.LOAD_PRESET))
async def load_preset(query: CallbackQuery, callback_data: PresetCallback, state: FSMContext):
    async with get_db() as db:
        preset_filters_service = FilterPresetService(db)
        preset = await preset_filters_service.get(callback_data.preset_id)
        serialized_preset = FilterPresetRead.model_validate(preset).model_dump(mode='json')
        await state.clear()
        await state.update_data(filters=serialized_preset)
        await state.set_state(FilterStates.setting_filters)

        await query.answer()
        await query.message.edit_text(
            "🎛️ **Set up your search filters:**\n\n"
            "Click on each filter below to set its value. "
            "You can edit any filter at any time before generating posts.",
            reply_markup=create_main_filters_keyboard(serialized_preset),
            parse_mode="Markdown"
        )

@presets_router.callback_query(PresetCallback.filter(F.action == PresetsActions.DELETE_PRESET))
async def delete_preset(query: CallbackQuery, callback_data: PresetCallback, state: FSMContext):
    async with get_db() as db:
        preset_filters_service = FilterPresetService(db)
        await preset_filters_service.delete(callback_data.preset_id)

        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(query.from_user.id))

        presets = await preset_filters_service.get_presets_for_user(user.id)

        serialized_presets = [FilterPresetRead.model_validate(preset).model_dump(mode='json') for preset in presets]
        await state.update_data(presets=serialized_presets)

        await query.answer("Preset deleted")
        await query.message.edit_text(f'📄 *Presets*\n'
                                      f'- Choose preset to load or delete', reply_markup=open_preset_keyboard(presets),
                                      parse_mode="Markdown")


