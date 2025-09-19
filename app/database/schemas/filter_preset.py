from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional


class FilterPresetCreate(BaseModel):
    name: str
    site: str | None = None
    make: str | None = None
    model: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    odo_from: int | None = None
    odo_to: int | None = None
    document: str | None = None
    transmission: str | None = None
    status: str | None = None
    user_id: int

class FilterPresetUpdate(BaseModel):
    site: Optional[str] = None

class FilterPresetRead(FilterPresetCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
