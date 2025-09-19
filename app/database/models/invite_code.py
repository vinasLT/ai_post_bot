from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.database.models import Base


class InviteCode(Base):
    __tablename__ = "invite_code"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code_hash: Mapped[str] = mapped_column(nullable=False)
    is_used: Mapped[bool] = mapped_column(default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))



