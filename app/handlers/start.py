import uuid
from datetime import datetime, UTC, timezone

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message

from app.database.crud.invite_code import InviteCodeService
from app.database.crud.user import UserService
from app.database.db.session import get_db
from app.database.schemas.invite_code import InviteCodeUpdate
from app.database.schemas.user import UserCreate
from app.keyboards.inline.main_menu import main_menu_keyboard
from app.services.hash_code import hash_secret

start_router = Router()


@start_router.message(CommandStart(deep_link=True))
async def start_command(message: Message, command: CommandObject):
    telegram_id = message.from_user.id
    args = command.args

    async with get_db() as db:
        invite_code_service = InviteCodeService(db)
        hashed_code = hash_secret(args)
        now = datetime.now(timezone.utc)
        invite_code = await invite_code_service.get_by_code_hash(hashed_code)
        if invite_code:
            if invite_code.is_used:
                await message.answer("Your link has already been used, ask for a new one.")
                return
            expires_at = invite_code.expires_at
            if expires_at.tzinfo is None or expires_at.tzinfo.utcoffset(expires_at) is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < now:
                await message.answer("Your link has expired, ask for a new one.")
                return

        else:
            await message.answer("Invalid link.")
            return

        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(telegram_id))
        if not user:
            await user_service.create(UserCreate(name=message.from_user.username, telegram_id=str(telegram_id),
                                                 user_uuid=str(uuid.uuid4())))
            await invite_code_service.update(invite_code.id, InviteCodeUpdate(is_used=True))

    await message.answer(f"Hello, your telegram id is {telegram_id}, args: {args}", reply_markup=main_menu_keyboard())

@start_router.message(CommandStart())
async def start_command_without_link(message: Message):
    telegram_id = message.from_user.id
    async with get_db() as db:
        user_service = UserService(db)
        user = await user_service.get_by_telegram_id(str(telegram_id))
        if user:
            await message.answer("You are already registered.", reply_markup=main_menu_keyboard())
            return