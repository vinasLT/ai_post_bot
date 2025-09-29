import datetime
from enum import Enum
from typing import Any

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.inline.presets import PresetsActions, PresetCallback


class FilterCallback(CallbackData, prefix="filter"):
    action: str
    filter_type: str
    value: str | None = None


class NavigationCallback(CallbackData, prefix="nav"):
    action: str



class FilterActions:
    SET = "set"
    EDIT = "edit"
    CUSTOM_INPUT = "custom"
    SET_NONE = "set_none"
    BACK = "back"
    CONFIRM = "confirm"
    SUMMARY = "summary"

    SAVE_PRESET = "save_preset"




class FilterTypes(str, Enum):
    SITE = "site"
    MAKE = "make"
    MODEL = "model"
    YEAR_FROM = "year_from"
    YEAR_TO = "year_to"
    ODO_FROM = "odo_from"
    ODO_TO = "odo_to"
    DOCUMENT = "document"
    TRANSMISSION = "transmission"
    STATUS = "status"
    AUCTION_DATE = "auction_date"

def get_human_readable_filter_type(filter_type: FilterTypes) -> str:
    """Get a human-readable filter type"""
    names = {
        FilterTypes.SITE: "🌐 Site",
        FilterTypes.MAKE: "🚗 Make",
        FilterTypes.MODEL: "🔧 Model",
        FilterTypes.YEAR_FROM: "📅 Year from",
        FilterTypes.YEAR_TO: "📅 Year to",
        FilterTypes.ODO_FROM: "🛣️ Odometer from",
        FilterTypes.ODO_TO: "🛣️ Odometer to",
        FilterTypes.DOCUMENT: '📄 Document',
        FilterTypes.TRANSMISSION: '⚙️ Transmission',
        FilterTypes.STATUS: '🔋 Status',
        FilterTypes.AUCTION_DATE: '⏳ Auction date',
    }
    return names.get(filter_type)

# Filter options
FILTER_OPTIONS = {
    FilterTypes.SITE: ["IAAI", "COPART"],
    FilterTypes.DOCUMENT: ["Salvage", "Clean"],
    FilterTypes.TRANSMISSION: ["Automatic", "Manual"],
    FilterTypes.STATUS: ["Run & Drive", "Starts", "Stationary"],
    FilterTypes.AUCTION_DATE: ["Only today", "From Today to Tomorrow"]
}

COMMON_MAKES = [
    "BMW", "Mercedes-Benz", "Audi", "Toyota", "Honda", "Ford",
    "Chevrolet", "Nissan", "Hyundai", "Volkswagen"
]




def get_default_filters() -> dict[str, Any]:
    """Return default filter values"""
    return {
        FilterTypes.SITE: None,
        FilterTypes.MAKE: None,
        FilterTypes.MODEL: None,
        FilterTypes.YEAR_FROM: None,
        FilterTypes.YEAR_TO: None,
        FilterTypes.ODO_FROM: None,
        FilterTypes.ODO_TO: None,
        FilterTypes.DOCUMENT: None,
        FilterTypes.TRANSMISSION: None,
        FilterTypes.STATUS: None,
        FilterTypes.AUCTION_DATE: None,
    }

def transform_auction_date_to_range(auction_date: str) -> dict[str, Any]:
    """Transform auction date to range"""
    today = datetime.date.today()
    if auction_date == "Only today":
        return {'auction_date_from': str(today), 'auction_date_to': str(today)}
    elif auction_date == "From Today to Tomorrow":
        return {'auction_date_from': str(today), 'auction_date_to': str(today + datetime.timedelta(days=1))}
    else:
        return {'auction_date_from': None, 'auction_date_to': None}


def create_main_filters_keyboard(filters: dict[str, Any]) -> InlineKeyboardMarkup:
    """Create the main filters selection keyboard"""
    keyboard = []

    for filter_type in FilterTypes:
        filter_text = get_human_readable_filter_type(filter_type)
        keyboard.append([InlineKeyboardButton(
            text=f'{filter_text}: {filters[filter_type] or "Not set"}',
            callback_data=FilterCallback(action=FilterActions.EDIT, filter_type=filter_type).pack()
        )])

    keyboard.append(
        [
            InlineKeyboardButton(
                text="📋 Show Summary",
                callback_data=FilterCallback(action=FilterActions.SUMMARY, filter_type="").pack()
            ),
            InlineKeyboardButton(
                text="✅ Generate Posts",
                callback_data=FilterCallback(action=FilterActions.CONFIRM, filter_type="").pack()
            )],


    )
    keyboard.append(
        [
            InlineKeyboardButton(
                text='💾 Save Preset',
                callback_data=FilterCallback(action=FilterActions.SAVE_PRESET, filter_type="").pack()
            ),
            InlineKeyboardButton(
                text='🔄 Load Preset',
                callback_data=PresetCallback(action=PresetsActions.GET_ALL_PRESETS).pack()
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_filter_options_keyboard(filter_type: str, current_value: str | None = None) -> InlineKeyboardMarkup:
    """Create keyboard for specific filter options"""
    keyboard = []

    if filter_type in FILTER_OPTIONS:
        options = FILTER_OPTIONS[filter_type]
        for option in options:
            emoji = "✅ " if current_value == option else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{emoji}{option}",
                callback_data=FilterCallback(action=FilterActions.SET, filter_type=filter_type, value=option).pack()
            )])
    elif filter_type == FilterTypes.MAKE:
        for make in COMMON_MAKES:
            emoji = "✅ " if current_value == make else ""
            keyboard.append([InlineKeyboardButton(
                text=f"{emoji}{make}",
                callback_data=FilterCallback(action=FilterActions.SET, filter_type=filter_type, value=make).pack()
            )])
        keyboard.append([InlineKeyboardButton(
            text="✏️ Enter custom make",
            callback_data=FilterCallback(action=FilterActions.CUSTOM_INPUT, filter_type=filter_type).pack()
        )])
    else:
        if current_value:
            keyboard.append([InlineKeyboardButton(
                text=f"Current: {current_value}",
                callback_data="current_value"
            )])
        keyboard.append([InlineKeyboardButton(
            text="✏️ Enter value",
            callback_data=FilterCallback(action=FilterActions.CUSTOM_INPUT, filter_type=filter_type).pack()
        )])

    keyboard.append([InlineKeyboardButton(
        text="⬅️ Back to filters",
        callback_data=FilterCallback(action=FilterActions.BACK, filter_type="").pack()
    )])

    keyboard.append([InlineKeyboardButton(
        text="✖️ Set None",
        callback_data=FilterCallback(action=FilterActions.SET_NONE, filter_type=filter_type).pack()
    )])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_to_filters_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⬅️ Back to filters",
            callback_data=FilterCallback(action=FilterActions.BACK, filter_type="").pack()
        )]
    ])



def create_summary_text(filters: dict[str, Any]) -> str:
    """Create summary text of all filters"""
    summary = "📋 **Filter Summary:**\n\n"

    for filter_type, value in filters.items():
        display_value = value if value else "Not set"
        try:
            summary+=get_human_readable_filter_type(FilterTypes(filter_type)) + f": {display_value}\n"
        except ValueError:
            continue


    return summary

INTEGER_FILTER_TYPES = {
    FilterTypes.YEAR_FROM,
    FilterTypes.YEAR_TO,
    FilterTypes.ODO_FROM,
    FilterTypes.ODO_TO
}

def is_integer_filter_type(filter_type: str | FilterTypes) -> bool:
    """Check if the filter type expects an integer value"""
    try:
        filter_type_enum = FilterTypes(filter_type)
    except ValueError:
        return False
    return filter_type_enum in INTEGER_FILTER_TYPES


def validate_filter_value(filter_type: str | FilterTypes, value: str) -> bool:
    """Validate the value for the given filter type. Integer fields must be integers."""
    if is_integer_filter_type(filter_type):
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False
    return True  # Non-integer fields are always valid
