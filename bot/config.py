from functools import lru_cache
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables / .env file.

    Add new settings here (admin IDs, Redis, webhook, ...) and the rest of
    the app can read them through get_settings().
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///bot.db"

    # Telegram user ids allowed to use /credit. In .env: ADMIN_IDS=111,222
    admin_ids: Annotated[list[int], NoDecode] = []

    # Exchange
    fee_bps: int = 0  # fee taken from the seller, in basis points (100 = 1%)
    min_price: int = 1_000  # Toman
    max_price: int = 10_000_000  # Toman
    qr_check: bool = True  # reject photos without a readable QR (needs opencv)

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _split_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [int(part) for part in value.replace(" ", "").split(",") if part]
        if isinstance(value, int):
            return [value]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
