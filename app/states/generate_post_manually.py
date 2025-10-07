from aiogram.fsm.state import StatesGroup, State


class GenerateManuallyStates(StatesGroup):
    set_lot = State()
    set_auction = State()