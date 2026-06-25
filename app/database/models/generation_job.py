import enum
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from .base import Base


class GenerationJobStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class GenerationJobType(str, enum.Enum):
    WITH_FILTERS = "with_filters"
    MANUALLY = "manually"
    ADD_COMMENT = "add_comment"
    GENERATE_IMAGE = "generate_image"
    PUBLISH_POST = "publish_post"


class GenerationJob(Base):
    __tablename__ = "generation_job"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_type: Mapped[GenerationJobType] = mapped_column(
        Enum(GenerationJobType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[GenerationJobStatus] = mapped_column(
        Enum(GenerationJobStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=GenerationJobStatus.PENDING,
    )
    user_uuid: Mapped[str] = mapped_column(String, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
