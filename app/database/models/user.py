from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.models import Base

if TYPE_CHECKING:
    from app.database.models.filter_preset import FilterPreset


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=True)
    user_uuid: Mapped[str] = mapped_column(nullable=False)
    telegram_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 default=lambda: datetime.now(timezone.utc))

    filter_presets: Mapped[list['FilterPreset']] = relationship(
        "FilterPreset", back_populates="user", uselist=True, lazy="selectin",
    )


