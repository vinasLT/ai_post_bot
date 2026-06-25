import asyncio
import base64
from typing import Any, Callable, Awaitable

from app.core.logger import intercept_stdlib_logging, logger
from app.database.crud.post import PostService
from app.database.db.session import get_db
from app.database.models.generation_job import GenerationJobType
from app.database.schemas.post import PostUpdate
from app.services.post_generation.generate_post_manually import process_post_manually
from app.services.post_generation.image_post_generator.generator import build_post
from app.services.post_generation.job_service import GenerationJobService
from app.services.post_generation.lang_chain_agent import run_flow
from app.services.post_generation.lang_chain_agent.serializer import SerializePost
from app.services.post_generation.lang_chain_agent.types import Filters
from app.services.post_generation.lang_chain_agent.utils import GeneratePostUtils
from app.services.post_generation.post_delivery_service import PostDeliveryService

POLL_INTERVAL_SECONDS = 2.0


async def _handle_with_filters(payload: dict[str, Any]) -> None:
    await run_flow(
        Filters(**payload["filters"]),
        payload["user_uuid"],
        payload["editable_message_id"],
    )


async def _handle_manually(payload: dict[str, Any]) -> None:
    await process_post_manually(
        payload["lot_id"],
        payload["site"],
        payload["user_uuid"],
        payload["message_id"],
    )


async def _handle_add_comment(payload: dict[str, Any]) -> None:
    post_id = payload["post_id"]
    comment = payload["comment"]
    user_uuid = payload["user_uuid"]
    editable_message_id = payload["editable_message_id"]
    async with get_db() as db:
        post_service = PostService(db)
        post = await post_service.get(post_id)
        await post_service.update(post_id, PostUpdate(comment=comment))
        serialized = GeneratePostUtils.generate_response_for_user([post])
        data = {
            "posts": serialized,
            "request_id": post.request_id,
            "message_id": editable_message_id,
            "user_uuid": user_uuid,
        }
    await PostDeliveryService.send_manually_generated_post(data)


async def _handle_generate_image(payload: dict[str, Any]) -> None:
    post_id = payload["post_id"]
    editable_message_id = payload["editable_message_id"]
    user_uuid = payload["user_uuid"]
    async with get_db() as db:
        post_service = PostService(db)
        post = await post_service.get(post_id)
        request_id = post.request_id
        images = post.images.split(",")
        text = SerializePost(post).serialize(for_image=True)
        image = build_post(images[:3], text, font_size=30, line_h=40)
    await PostDeliveryService.send_image_generated(
        {
            "image": base64.b64encode(image).decode("ascii"),
            "message_id": editable_message_id,
            "post_id": post_id,
            "user_uuid": user_uuid,
            "request_id": request_id,
        }
    )


async def _handle_publish_post(payload: dict[str, Any]) -> None:
    post_id = payload["post_id"]
    async with get_db() as db:
        post_service = PostService(db)
        post = await post_service.get(post_id)
        await post_service.update(post_id, PostUpdate(is_posted=True))
        serializer = SerializePost(post)
        forum_payload = {
            "images": post.images.split(",")[:3],
            "texts_by_language": serializer.texts_by_language_for_publish(),
        }
    await PostDeliveryService.publish_to_forum(forum_payload)


JOB_HANDLERS: dict[GenerationJobType, Callable[[dict[str, Any]], Awaitable[None]]] = {
    GenerationJobType.WITH_FILTERS: _handle_with_filters,
    GenerationJobType.MANUALLY: _handle_manually,
    GenerationJobType.ADD_COMMENT: _handle_add_comment,
    GenerationJobType.GENERATE_IMAGE: _handle_generate_image,
    GenerationJobType.PUBLISH_POST: _handle_publish_post,
}


async def process_job(job_id: int, job_type: GenerationJobType, payload: dict[str, Any]) -> None:
    handler = JOB_HANDLERS.get(job_type)
    if handler is None:
        raise ValueError(f"Unknown job type: {job_type}")
    await handler(payload)


async def worker_loop() -> None:
    intercept_stdlib_logging()
    logger.info("Generation worker started")
    while True:
        try:
            async with get_db() as db:
                job_service = GenerationJobService(db)
                job = await job_service.claim_next()
                if job is None:
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
                    continue
                job_id = job.id
                job_type = job.job_type
                payload = job.payload
                user_uuid = job.user_uuid

            try:
                await process_job(job_id, job_type, payload)
                async with get_db() as db:
                    await GenerationJobService(db).mark_done(job_id)
            except Exception as exc:
                logger.exception(
                    "Generation job failed",
                    job_id=job_id,
                    job_type=job_type.value,
                    user_uuid=user_uuid,
                )
                async with get_db() as db:
                    await GenerationJobService(db).mark_failed(job_id, str(exc))
                try:
                    await PostDeliveryService.send_error(
                        user_uuid=user_uuid,
                        error_message=str(exc),
                        request_id=payload.get("request_id"),
                    )
                except Exception:
                    logger.exception(
                        "Failed to notify user about generation job error",
                        job_id=job_id,
                        user_uuid=user_uuid,
                    )
        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def main() -> None:
    await worker_loop()


if __name__ == "__main__":
    asyncio.run(main())
