from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserCreate(BaseModel):
    user_uuid: str
    name: str
    telegram_id: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    telegram_id: Optional[str] = None

class UserRead(UserCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
