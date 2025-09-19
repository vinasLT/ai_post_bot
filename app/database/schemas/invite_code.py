from datetime import datetime

from pydantic import BaseModel, ConfigDict
from typing import Optional


class InviteCodeCreate(BaseModel):
    code_hash: str
    is_used: bool | None = None
    expires_at: datetime
    created_at: datetime | None = None

class InviteCodeUpdate(BaseModel):
    is_used: Optional[bool] = None

class InviteCodeRead(InviteCodeCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)
