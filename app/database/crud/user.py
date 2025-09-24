from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models.user import User
from app.database.schemas.user import UserCreate, UserUpdate


class UserService(BaseService[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_telegram_id(self, telegram_id: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_uuid(self, user_uuid: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.user_uuid == user_uuid)
        )
        return result.scalar_one_or_none()

