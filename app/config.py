from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict



class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"

class Settings(BaseSettings):
    #Application
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

    # telegram channel
    TELEGRAM_CHANNEL_ID: str = '-1002852542718'


    #rpc_server
    RPC_AUCTION_API_URL: str = "localhost:50052"


    # secret key
    SECRET_BOT_POST_GENERATOR_KEY: str = "secret-kjfh3h8974fhiosudfh9278fhko"

    # aiogram
    TELEGRAM_BOT_TOKEN: str = '6710436824:AAFoMfr1BN6UTJEJdynntjjGHLypTBI-2A8'

    model_config = SettingsConfigDict(env_file="../.env")


settings = Settings()