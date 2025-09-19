from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models.invite_code import InviteCode
from app.database.schemas.invite_code import InviteCodeCreate, InviteCodeUpdate


class InviteCodeService(BaseService[InviteCode, InviteCodeCreate, InviteCodeUpdate]):
    CODE_EXPIRE_AFTER_SECONDS = 60 * 30
    CODE_LENGTH = 6

    def __init__(self, session: AsyncSession):
        super().__init__(InviteCode, session)

    async def get_by_code_hash(self, code_hash: str) -> InviteCode:
        result = await self.session.execute(
            select(InviteCode).where(InviteCode.code_hash == code_hash)
        )
        return result.scalar_one_or_none()

