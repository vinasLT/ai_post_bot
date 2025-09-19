from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models.filter_preset import FilterPreset
from app.database.schemas.filter_preset import FilterPresetCreate, FilterPresetUpdate


class FilterPresetService(BaseService[FilterPreset, FilterPresetCreate, FilterPresetUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(FilterPreset, session)

    async def get_presets_for_user(self, user_id: int) -> list[FilterPreset]:
        result = await self.session.execute(
            select(FilterPreset).where(FilterPreset.user_id == user_id)
        )
        return result.scalars().all()



