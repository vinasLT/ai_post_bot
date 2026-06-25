from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.db.session import get_db
from app.database.models.generation_job import (
    GenerationJob,
    GenerationJobStatus,
    GenerationJobType,
)


class GenerationJobService(BaseService[GenerationJob, Any, Any]):
    def __init__(self, session: AsyncSession):
        super().__init__(GenerationJob, session)

    async def enqueue(
        self,
        job_type: GenerationJobType | str,
        payload: dict[str, Any],
        user_uuid: str,
    ) -> int:
        if isinstance(job_type, str):
            job_type = GenerationJobType(job_type)
        job = GenerationJob(
            job_type=job_type,
            payload=payload,
            status=GenerationJobStatus.PENDING,
            user_uuid=user_uuid,
        )
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job.id

    async def claim_next(self) -> GenerationJob | None:
        stmt = (
            select(GenerationJob)
            .where(GenerationJob.status == GenerationJobStatus.PENDING)
            .order_by(GenerationJob.id)
            .limit(1)
        )
        bind = self.session.get_bind()
        if bind is not None and bind.dialect.name == "postgresql":
            stmt = stmt.with_for_update(skip_locked=True)

        result = await self.session.execute(stmt)
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = GenerationJobStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def mark_done(self, job_id: int) -> None:
        job = await self.get(job_id)
        if job is None:
            return
        job.status = GenerationJobStatus.DONE
        job.finished_at = datetime.now(UTC)
        await self.session.commit()

    async def mark_failed(self, job_id: int, error_message: str) -> None:
        job = await self.get(job_id)
        if job is None:
            return
        job.status = GenerationJobStatus.FAILED
        job.error_message = error_message[:2000]
        job.finished_at = datetime.now(UTC)
        await self.session.commit()


async def enqueue_generation_job(
    job_type: GenerationJobType | str,
    payload: dict[str, Any],
    user_uuid: str,
) -> int:
    async with get_db() as db:
        service = GenerationJobService(db)
        return await service.enqueue(job_type, payload, user_uuid)
