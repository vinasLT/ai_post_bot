from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.keyboards.inline.choose_auction import choose_auction_keyboard, ChooseAuctionCallback
from app.keyboards.inline.main_menu import MainMenuActions, MainMenuCallback
from app.keyboards.inline.post_this_post import PostThisPostCallback, GeneratePostImageCallback
from app.rpc_client.auction_api import ApiRpcClient
from app.services.rabbit.pulisher import RabbitMQPublisher
from app.states.filter_states import FilterStates
from app.states.generate_post_manually import GenerateManuallyStates

generate_post_manually_router = Router()

@generate_post_manually_router.callback_query(MainMenuCallback.filter(F.action == MainMenuActions.GENERATE_POST_MANUALLY))
async def generate_post_manually(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await query.message.answer("Send VIN or Lot ID:")
    await query.answer()
    await state.set_state(GenerateManuallyStates.set_lot)

@generate_post_manually_router.message(GenerateManuallyStates.set_lot)
async def process_lot_id(message: Message, state: FSMContext):
    vin_or_lot_id = message.text
    async with ApiRpcClient() as client:
        lot = await client.get_lot_by_vin_or_lot_id(vin_or_lot_id)
        if lot.lot:
            await message.answer('Choose auction:', reply_markup=choose_auction_keyboard(vin_or_lot_id))
            await state.set_state(GenerateManuallyStates.set_auction)
        else:
            await message.answer("❌ No such lot or VIN\n"
                                 "Send another VIN or Lot ID:")



@generate_post_manually_router.callback_query(ChooseAuctionCallback.filter())
async def process_lot_id(query: CallbackQuery, callback_data: ChooseAuctionCallback, state: FSMContext):
    vin_or_lot_id = callback_data.lot_id_or_vin
    auction = callback_data.auction
    async with ApiRpcClient() as client:
        lot = await client.get_lot_by_vin_or_lot_id(vin_or_lot_id, auction)

    if not lot.lot:
        await state.set_state(GenerateManuallyStates.set_lot)
        await query.message.edit_text("❌ No such lot or VIN\n"
                                 "Send another VIN or Lot ID:")
        await query.answer()
        return
    elif len(lot.lot) == 1:
        lot = lot.lot[0]
        async with get_db() as db:
            user_service = UserService(db)
            user = await user_service.get_by_telegram_id(str(query.from_user.id))
        generating_message = await query.message.edit_text("Generating post...")
        payload = {
            'lot_id': lot.lot_id,
            'site': lot.base_site,
            'user_uuid': user.user_uuid,
            'message_id': generating_message.message_id
        }
        publisher = RabbitMQPublisher()
        await publisher.connect()
        await publisher.publish('posts_bot.generate_post.manually', payload)
        await query.answer()
        return

@generate_post_manually_router.callback_query(PostThisPostCallback.filter(F.add_comment == True))
async def add_comment(query: CallbackQuery, callback_data: PostThisPostCallback, state: FSMContext):
    print('ADD COMMENT')
    await state.update_data(
        {
            'post_id': callback_data.post_id,
            'request_id': callback_data.request_id,
        }
    )

    await query.message.edit_text("Add comment:")
    await state.set_state(GenerateManuallyStates.set_comment)
    await query.answer()

@generate_post_manually_router.message(GenerateManuallyStates.set_comment)
async def save_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    post_id = data.get('post_id')
    request_id = data.get('request_id')
    comment = message.text
    async with get_db() as db:
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(message.from_user.id))

    editable_message = await message.answer("Generating post...")
    payload = {
        'post_id': post_id,
        'comment': comment,
        'user_uuid': user.user_uuid,
        'request_id': request_id,
        'editable_message_id': editable_message.message_id,
    }
    publisher = RabbitMQPublisher()
    await publisher.connect()
    await publisher.publish('posts_bot.generate_post.manually.add_comment', payload)

    await state.clear()

@generate_post_manually_router.callback_query(GeneratePostImageCallback.filter())
async def save_comment(query: CallbackQuery, callback_data: PostThisPostCallback):
    editable_message = await query.message.edit_text("Generating image...")

    async with get_db() as db:
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(query.from_user.id))

    payload = {
        'post_id': callback_data.post_id,
        'request_id': callback_data.request_id,
        'user_uuid': user.user_uuid,
        'editable_message_id': editable_message.message_id
    }

    publisher = RabbitMQPublisher()
    await publisher.connect()
    await publisher.publish('posts_bot.generate_post.manually.generate_image', payload)

    await query.answer()




