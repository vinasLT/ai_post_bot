import json
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"


# Same order as post texts in ai_post_generator (LT, PL, LV, ET, UK, EN).
FORUM_TOPIC_LANG_ORDER: tuple[str, ...] = ("lt", "pl", "lv", "et", "uk", "en")


def parse_forum_topic_ids_by_lang(raw: str) -> dict[str, int]:
    """Parse TELEGRAM_TOPIC_IDS_JSON as {"lt": 2, "pl": 4, ...} with all six language keys."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("TELEGRAM_TOPIC_IDS_JSON is empty")
    data: Any = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(
            'TELEGRAM_TOPIC_IDS_JSON must be a JSON object, e.g. {"lt":2,"pl":4,"lv":6,"et":8,"uk":10,"en":12}'
        )
    missing = [k for k in FORUM_TOPIC_LANG_ORDER if k not in data]
    if missing:
        raise ValueError(
            "TELEGRAM_TOPIC_IDS_JSON object missing keys: "
            + ", ".join(missing)
            + f"; expected: {', '.join(FORUM_TOPIC_LANG_ORDER)}"
        )
    return {lang: int(data[lang]) for lang in FORUM_TOPIC_LANG_ORDER}


def parse_forum_topic_ids_json(raw: str) -> tuple[int, ...]:
    """Return thread ids in lt, pl, lv, et, uk, en order."""
    by_lang = parse_forum_topic_ids_by_lang(raw)
    return tuple(by_lang[lang] for lang in FORUM_TOPIC_LANG_ORDER)


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "post-generator-bot"
    DEBUG: bool = True
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    @property
    def enable_docs(self) -> bool:
        return self.ENVIRONMENT in [Environment.DEVELOPMENT]

    @property
    def use_sqlite_db(self) -> bool:
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_NAME: str = "test_db"
    DB_USER: str = "postgres"
    DB_PASS: str = "testpass"

    # gRPC
    RPC_AUCTION_API_URL: str = "localhost:50052"
    RPC_CALCULATOR_URL: str = "localhost:50051"
    
    # OpenAI (post generation LangGraph)
    OPENAI_API_KEY: str = ""

    # Telegram forum — set in .env
    TELEGRAM_FORUM_CHAT_ID: str = ""
    TELEGRAM_TOPIC_IDS_JSON: str = ""

    @field_validator("TELEGRAM_TOPIC_IDS_JSON", mode="after")
    @classmethod
    def _validate_topic_ids_json(cls, v: str) -> str:
        parse_forum_topic_ids_by_lang(v)
        return v

    @property
    def forum_topic_thread_ids_ordered(self) -> tuple[int, ...]:
        return parse_forum_topic_ids_json(self.TELEGRAM_TOPIC_IDS_JSON)

    @property
    def forum_topic_ids_by_lang(self) -> dict[str, int]:
        return parse_forum_topic_ids_by_lang(self.TELEGRAM_TOPIC_IDS_JSON)

    # secret key (set in .env)
    SECRET_BOT_POST_GENERATOR_KEY: str = ""

    # aiogram (set in .env)
    TELEGRAM_BOT_TOKEN: str = ""
    # Each album photo counts toward ~20 msgs/min per group; pace multi-language publishes.
    FORUM_PUBLISH_SECONDS_PER_IMAGE: float = 3.0
    TELEGRAM_RETRY_AFTER_MAX_RETRIES: int = 5

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        extra="ignore",
    )


settings = Settings()
