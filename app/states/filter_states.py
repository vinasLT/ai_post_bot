from aiogram.fsm.state import StatesGroup, State


class FilterStates(StatesGroup):
    setting_filters = State()
    waiting_custom_input = State()
    waiting_preset_name = State()