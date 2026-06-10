import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


# Same order as post texts in ai_post_generator (LT, PL, LV, ET, UK, EN).
FORUM_TOPIC_LANG_ORDER: tuple[str, ...] = ("lt", "pl", "lv", "et", "uk", "en")


def parse_forum_topic_ids_json(raw: str) -> tuple[int, ...]:
    """Parse TELEGRAM_TOPIC_IDS_JSON: either a 6-int array or an object with lt,pl,lv,et,uk,en keys."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("TELEGRAM_TOPIC_IDS_JSON is empty")
    data: Any = json.loads(text)
    n = len(FORUM_TOPIC_LANG_ORDER)
    if isinstance(data, list):
        if len(data) != n:
            raise ValueError(
                f"TELEGRAM_TOPIC_IDS_JSON array must have {n} integers "
                f"(order: {', '.join(FORUM_TOPIC_LANG_ORDER)})"
            )
        return tuple(int(x) for x in data)
    if isinstance(data, dict):
        missing = [k for k in FORUM_TOPIC_LANG_ORDER if k not in data]
        if missing:
            raise ValueError(
                "TELEGRAM_TOPIC_IDS_JSON object missing keys: "
                + ", ".join(missing)
                + f"; expected: {', '.join(FORUM_TOPIC_LANG_ORDER)}"
            )
        return tuple(int(data[k]) for k in FORUM_TOPIC_LANG_ORDER)
    raise ValueError("TELEGRAM_TOPIC_IDS_JSON must be a JSON array or object")


def parse_forum_topic_ids_by_lang(raw: str) -> dict[str, int]:
    """Map language code to forum topic thread id."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("TELEGRAM_TOPIC_IDS_JSON is empty")
    data: Any = json.loads(text)
    if isinstance(data, dict):
        missing = [k for k in FORUM_TOPIC_LANG_ORDER if k not in data]
        if missing:
            raise ValueError(
                "TELEGRAM_TOPIC_IDS_JSON object missing keys: "
                + ", ".join(missing)
                + f"; expected: {', '.join(FORUM_TOPIC_LANG_ORDER)}"
            )
        return {lang: int(data[lang]) for lang in FORUM_TOPIC_LANG_ORDER}
    if isinstance(data, list):
        thread_ids = parse_forum_topic_ids_json(raw)
        return dict(zip(FORUM_TOPIC_LANG_ORDER, thread_ids))
    raise ValueError("TELEGRAM_TOPIC_IDS_JSON must be a JSON array or object")


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "post-generator-bot"
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    @property
    def enable_docs(self) -> bool:
        return self.ENVIRONMENT in [Environment.DEVELOPMENT]

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "test_db"
    DB_USER: str = "postgres"
    DB_PASS: str = "testpass"

    # Rabbitmq
    RABBITMQ_URL: str = "amqp://guest:guest@localhost/"
    RABBITMQ_EXCHANGE_NAME: str = "events"
    RABBITMQ_QUEUE_NAME: str = "post_generator_bot"

    # Telegram forum supergroup (topics enabled) — same numeric id style as -100…
    TELEGRAM_FORUM_CHAT_ID: str = "-1002852542718"
    # JSON: [lt,pl,lv,et,uk,en] thread ids OR {"lt":2,"pl":3,...}
    TELEGRAM_TOPIC_IDS_JSON: str = "[1,2,3,4,5,6]"

    @field_validator("TELEGRAM_TOPIC_IDS_JSON", mode="after")
    @classmethod
    def _validate_topic_ids_json(cls, v: str) -> str:
        parse_forum_topic_ids_json(v)
        return v

    @property
    def forum_topic_thread_ids_ordered(self) -> tuple[int, ...]:
        return parse_forum_topic_ids_json(self.TELEGRAM_TOPIC_IDS_JSON)

    @property
    def forum_topic_ids_by_lang(self) -> dict[str, int]:
        return parse_forum_topic_ids_by_lang(self.TELEGRAM_TOPIC_IDS_JSON)

    # rpc_server
    RPC_AUCTION_API_URL: str = "localhost:50052"

    # secret key
    SECRET_BOT_POST_GENERATOR_KEY: str = "secret-kjfh3h8974fhiosudfh9278fhko"

    # aiogram
    TELEGRAM_BOT_TOKEN: str = "6710436824:AAFBqoqwfcEBNxA1LsjajoT1V2y5DGFXBmo"

    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parent.parent / ".env")


settings = Settings()
