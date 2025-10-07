from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.keyboards.inline.choose_auction import choose_auction_keyboard, ChooseAuctionCallback
from app.keyboards.inline.main_menu import MainMenuActions, MainMenuCallback
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
        if len(lot.lot) >= 2:
            await message.answer('Choose auction:', reply_markup=choose_auction_keyboard(vin_or_lot_id))
            await state.set_state(GenerateManuallyStates.set_auction)
        elif len(lot.lot) == 1:
            async with get_db() as db:
                user_service = UserService(db)
                user = await user_service.get_by_telegram_id(str(message.from_user.id))
            generating_message = await message.answer("Generating post...")
            payload = {
                'lot_id': lot.lot[0].lot_id,
                'site': lot.lot[0].base_site,
                'user_uuid': user.user_uuid,
                'message_id': generating_message.message_id
            }
            publisher = RabbitMQPublisher()
            await publisher.connect()
            await publisher.publish('posts_bot.generate_post.manually', payload)
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
