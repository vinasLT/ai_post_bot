from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext


from app.database.crud.filters_preset import FilterPresetService
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.database.schemas.filter_preset import FilterPresetCreate
from app.keyboards.inline.main_menu import MainMenuCallback, MainMenuActions
from app.keyboards.inline.post_generator_filters import get_default_filters, create_main_filters_keyboard, \
    FilterCallback, FilterActions, create_filter_options_keyboard, FilterTypes, \
    create_summary_text, back_to_filters_keyboard, get_human_readable_filter_type, validate_filter_value, \
    transform_auction_date_to_range
from app.services.rabbit.pulisher import RabbitMQPublisher
from app.states.filter_states import FilterStates

generate_posts_with_filters_router = Router()


@generate_posts_with_filters_router.callback_query(
    MainMenuCallback.filter(F.action == MainMenuActions.GENERATE_POST_WITH_FILTERS))
async def generate_posts_with_filters(query: CallbackQuery, callback_data: MainMenuCallback, state: FSMContext):
    """Initialize the filter selection process"""
    await query.answer()
    data = await state.get_data()
    filters = data.get('filters', get_default_filters())
    await state.update_data(filters=filters)
    await state.set_state(FilterStates.setting_filters)

    await query.message.edit_text(
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value. "
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    MainMenuCallback.filter(F.action == MainMenuActions.GENERATE_POST_WITH_FILTERS_IN_NEW_MESSAGE))
async def generate_posts_with_filters(query: CallbackQuery, callback_data: MainMenuCallback, state: FSMContext):
    await query.answer()
    data = await state.get_data()
    filters = data.get('filters', get_default_filters())
    await state.update_data(filters=filters)
    await state.set_state(FilterStates.setting_filters)

    await query.message.answer(
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value. "
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )



@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.EDIT))
async def edit_filter(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Handle filter editing"""
    await query.answer()

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    filter_type = callback_data.filter_type
    current_value = filters.get(filter_type)

    filter_name = get_human_readable_filter_type(FilterTypes(filter_type))

    await query.message.edit_text(
        f"🎛️ **Setting {filter_name}**\n\n"
        f"Current value: {current_value or 'Not set'}\n\n"
        "Choose an option below:",
        reply_markup=create_filter_options_keyboard(filter_type, current_value),
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.SET_NONE))
async def edit_filter(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    await query.answer()

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    filters[callback_data.filter_type] = None

    await state.update_data(filters=filters)

    await query.message.edit_text(
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value. "
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )

@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.SET))
async def set_filter_value(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Set a filter value"""
    await query.answer("✅ Filter updated!")

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    # Update the filter
    filters[callback_data.filter_type] = callback_data.value
    await state.update_data(filters=filters)

    # Return to main filters view
    await query.message.edit_text(
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value. "
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.CUSTOM_INPUT))
async def request_custom_input(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Request custom input for a filter"""
    await query.answer()

    filter_name = get_human_readable_filter_type(FilterTypes(callback_data.filter_type))
    await state.update_data(current_filter_type=callback_data.filter_type)
    await state.set_state(FilterStates.waiting_custom_input)

    placeholder_text = {
        FilterTypes.MODEL: "e.g., 1 Series, X5, A4, etc.",
        FilterTypes.YEAR_FROM: "e.g., 2015",
        FilterTypes.YEAR_TO: "e.g., 2023",
        FilterTypes.ODO_FROM: "e.g., 10000",
        FilterTypes.ODO_TO: "e.g., 50000",
        FilterTypes.MAKE: "e.g., BMW, Toyota, etc."
    }.get(callback_data.filter_type, "")

    await query.message.edit_text(
        f"✏️ **Enter {filter_name}**\n\n"
        f"Please type the value for {filter_name}.\n"
        f"{placeholder_text}\n\n"
        "Send your message now:",
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.message(FilterStates.waiting_custom_input)
async def handle_custom_input(message, state: FSMContext):
    """Handle custom input from user"""
    data = await state.get_data()
    filters = data.get('filters', get_default_filters())
    current_filter_type = data.get('current_filter_type')
    if current_filter_type:
        is_valid = validate_filter_value(FilterTypes(current_filter_type), message.text.strip())
        if not is_valid:
            await message.answer(
                '❌ This Value must be number, try again'
            )
            return
        # Update the filter with user input
        filters[current_filter_type] = message.text.strip()
        await state.update_data(filters=filters)

    await state.set_state(FilterStates.setting_filters)

    await message.answer(
        "✅ Filter updated!\n\n"
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value.\n"
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.BACK))
async def back_to_filters(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Return to main filters view"""
    await query.answer()

    await state.set_state(FilterStates.setting_filters)

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    await query.message.edit_text(
        "🎛️ **Set up your search filters:**\n\n"
        "Click on each filter below to set its value. "
        "You can edit any filter at any time before generating posts.",
        reply_markup=create_main_filters_keyboard(filters),
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.SUMMARY))
async def show_summary(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Show filter summary"""
    await query.answer()

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    summary_text = create_summary_text(filters)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="⬅️ Back to filters",
                callback_data=FilterCallback(action=FilterActions.BACK, filter_type="").pack()
            ),
            InlineKeyboardButton(
                text="✅ Generate Posts",
                callback_data=FilterCallback(action=FilterActions.CONFIRM, filter_type="").pack()
            )
        ]
    ])

    await query.message.edit_text(
        summary_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


@generate_posts_with_filters_router.callback_query(
    FilterCallback.filter(F.action == FilterActions.CONFIRM))
async def confirm_and_generate(query: CallbackQuery, callback_data: FilterCallback, state: FSMContext):
    """Confirm filters and start generation"""
    await query.answer("🚀 Starting post generation...")

    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    # Check if required filters are set (you can customize this)
    response = await is_all_required_filters(query.message, filters)
    if not response:
        return


    summary_text = create_summary_text(filters)

    await query.message.edit_text(
        f"✅ **Filters confirmed!**\n\n"
        f"{summary_text}\n"
        f"🚀 Starting post generation with these filters...\n\n"
        f"This may take a 1-2 minutes or less! Please wait.",
        reply_markup=back_to_filters_keyboard()
    )
    async with get_db() as db:
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(query.from_user.id))

    publisher = RabbitMQPublisher()
    await publisher.connect()
    auction_date = filters.get('auction_date')
    filters.update(transform_auction_date_to_range(auction_date))
    payload = {
        'filters': filters,
        'editable_message_id': query.message.message_id,
        'user_uuid': user.user_uuid
    }
    await publisher.publish(routing_key='posts_bot.generate_post.with_filters', payload=payload)
    await publisher.close()


async def is_all_required_filters(message: Message, filters: dict) -> bool:
    required_filters = [FilterTypes.SITE, FilterTypes.MAKE, FilterTypes.YEAR_FROM,
                        FilterTypes.YEAR_TO]
    missing_filters = [get_human_readable_filter_type(f) for f in required_filters if not filters.get(f)]

    if missing_filters:
        await message.edit_text(
            f"⚠️ **Missing required filters:**\n\n"
            f"Please set the following filters before generating posts:\n"
            f"• {', '.join(missing_filters)}\n\n"
            "Click the button below to go back and set these filters.",
            reply_markup=back_to_filters_keyboard()
        )
        return False
    return True


@generate_posts_with_filters_router.callback_query(FilterCallback.filter(F.action == FilterActions.SAVE_PRESET))
async def save_preset(query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    filters = data.get('filters', get_default_filters())

    summary_text = create_summary_text(filters)

    response = await is_all_required_filters(query.message, filters)
    if not response:
        return

    await query.message.edit_text(f'{summary_text}\n'
                               f'Set name for you preset', reply_markup=back_to_filters_keyboard())
    await state.set_state(FilterStates.waiting_preset_name)
    await query.answer()

@generate_posts_with_filters_router.message(FilterStates.waiting_preset_name)
async def save_preset_name(message, state: FSMContext):
    data = await state.get_data()
    filters = data.get('filters', get_default_filters())
    preset_name = message.text

    async with get_db() as db:
        preset_filters_service = FilterPresetService(db)
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(message.from_user.id))
        data = {}
        for key, value in filters.items():
            data[key] = value
        data['user_id'] = user.id
        data['name'] = preset_name

        await preset_filters_service.create(FilterPresetCreate(**data))

    await state.set_state(FilterStates.setting_filters)

    await message.answer(f'Preset *"{preset_name}"* saved\n'
                         f'You can go back and continue generating posts with different filters', reply_markup=back_to_filters_keyboard())







