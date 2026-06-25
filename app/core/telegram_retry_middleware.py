import asyncio
from typing import TYPE_CHECKING

from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods.base import Response, TelegramMethod, TelegramType

from app.core.logger import logger

if TYPE_CHECKING:
    from aiogram import Bot


class RetryAfterMiddleware(BaseRequestMiddleware):
    """Retry Telegram API calls when flood control returns retry_after."""

    def __init__(self, max_retries: int = 5) -> None:
        self._max_retries = max_retries

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: "Bot",
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        attempt = 0
        while True:
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as exc:
                if attempt >= self._max_retries:
                    logger.error(
                        "Telegram flood control: max retries exceeded",
                        extra={
                            "method": type(method).__name__,
                            "retry_after": exc.retry_after,
                            "attempts": attempt + 1,
                        },
                    )
                    raise

                logger.warning(
                    "Telegram flood control: waiting before retry",
                    extra={
                        "method": type(method).__name__,
                        "retry_after": exc.retry_after,
                        "attempt": attempt + 1,
                    },
                )
                await asyncio.sleep(exc.retry_after)
                attempt += 1
