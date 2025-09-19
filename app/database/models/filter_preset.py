from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.models import Base

if TYPE_CHECKING:
    from app.database.models import User

class FilterPreset(Base):
    __tablename__ = "filter_preset"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(nullable=False)

    site: Mapped[str | None] = mapped_column(nullable=True)
    make: Mapped[str | None] = mapped_column(nullable=True)
    model: Mapped[str | None] = mapped_column(nullable=True)
    year_from: Mapped[int | None] = mapped_column(nullable=True)
    year_to: Mapped[int | None] = mapped_column(nullable=True)
    odo_from: Mapped[int | None] = mapped_column(nullable=True)
    odo_to: Mapped[int | None] = mapped_column(nullable=True)
    document: Mapped[str | None] = mapped_column(nullable=True)
    transmission: Mapped[str | None] = mapped_column(nullable=True)
    status: Mapped[str | None] = mapped_column(nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False,
                                                 default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(
        "User", back_populates="filter_presets", lazy="selectin"
    )
