import asyncio
from typing import Any

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMediaPhoto

from app.config import settings
from app.core.bot import bot
from app.core.logger import logger

_forum_publish_lock = asyncio.Lock()


def _pace_seconds_after_media_group(media_count: int) -> float:
    """Delay between topic posts in the same forum (~20 msgs/min group limit)."""
    return max(1.0, media_count * settings.FORUM_PUBLISH_SECONDS_PER_IMAGE)


class ForumPublishService:
    async def publish(self, payload: dict[str, Any]) -> None:
        texts_by_language = payload.get("texts_by_language") or []
        images = payload.get("images") or []

        if not texts_by_language or not images:
            logger.error(
                "publish_post payload missing texts_by_language or images",
                extra={"keys": list(payload.keys())},
            )
            return

        topic_by_lang = settings.forum_topic_ids_by_lang
        chat_id = settings.TELEGRAM_FORUM_CHAT_ID

        async with _forum_publish_lock:
            for entry in texts_by_language:
                lang = (entry.get("lang") or "").lower()
                text = entry.get("text") or ""
                message_thread_id = topic_by_lang.get(lang)

                if message_thread_id is None:
                    logger.warning(
                        "Unknown language in publish_post payload, skipping",
                        extra={"lang": lang, "known_langs": list(topic_by_lang.keys())},
                    )
                    continue

                media = self._build_media_group(images, text)
                await self._send_to_topic(
                    chat_id, media, message_thread_id, lang, images, text
                )
                await asyncio.sleep(_pace_seconds_after_media_group(len(media)))

    def _build_media_group(
        self,
        images: list[str],
        text: str,
        parse_mode: ParseMode | None = ParseMode.HTML,
    ) -> list[InputMediaPhoto]:
        media: list[InputMediaPhoto] = []
        for i, url in enumerate(images[:5]):
            if i == 0:
                media.append(
                    InputMediaPhoto(media=url, caption=text, parse_mode=parse_mode)
                )
            else:
                media.append(InputMediaPhoto(media=url))
        return media

    async def _send_to_topic(
        self,
        chat_id: str,
        media: list[InputMediaPhoto],
        message_thread_id: int,
        lang: str,
        images: list[str],
        text: str,
    ) -> None:
        try:
            await bot.send_media_group(
                chat_id=chat_id,
                media=media,
                message_thread_id=message_thread_id,
            )
            logger.info(
                "Forum publish succeeded",
                extra={
                    "lang": lang,
                    "message_thread_id": message_thread_id,
                    "image_count": len(media),
                },
            )
        except TelegramBadRequest as e:
            if "can't parse entities" not in str(e).lower():
                logger.exception(
                    "Forum publish failed for language topic",
                    extra={
                        "lang": lang,
                        "message_thread_id": message_thread_id,
                        "error": str(e),
                    },
                )
                raise

            plain_media = self._build_media_group(images, text, parse_mode=None)
            await bot.send_media_group(
                chat_id=chat_id,
                media=plain_media,
                message_thread_id=message_thread_id,
            )
            logger.info(
                "Forum publish succeeded with plain text fallback",
                extra={
                    "lang": lang,
                    "message_thread_id": message_thread_id,
                    "image_count": len(plain_media),
                },
            )
