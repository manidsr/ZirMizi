from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file.

    Add new settings here (admin IDs, Redis, webhook, ...) and the rest of
    the app can read them through get_settings().
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///bot.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
