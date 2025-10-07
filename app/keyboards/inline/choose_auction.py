from enum import Enum

from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Auctions(str, Enum):
    COPART = 'copart'
    IAAI = 'iaai'

class ChooseAuctionCallback(CallbackData, prefix="main_menu"):
    auction: str
    lot_id_or_vin: str | None = None

def choose_auction_keyboard(lot_id_or_vin: str | None = None):
    builder = InlineKeyboardBuilder()
    builder.button(text="IAAI",
                   callback_data=ChooseAuctionCallback(auction=Auctions.IAAI, lot_id_or_vin=lot_id_or_vin).pack())
    builder.button(text="COPART", callback_data=ChooseAuctionCallback(auction=Auctions.COPART, lot_id_or_vin=lot_id_or_vin).pack())
    builder.adjust(1)
    return builder.as_markup()
