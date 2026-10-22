"""Application configuration.

Settings come from (highest priority first): real environment variables, the
``.env`` file, then the defaults below. ``pydantic-settings`` reads and
type-converts them (e.g. the string "8001" becomes the int 8001) and fails
fast at startup if a value is invalid.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Field names map to environment variables case-insensitively (LOG_LEVEL -> log_level).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "production"] = "development"
    host: str = "127.0.0.1"
    port: int = 8001
    # A relative path, resolved against the directory you start the server from.
    database_url: str = "sqlite:///./data/expense_tracker.db"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Report responses are cached this long (cleared on any write). 0 disables the cache.
    report_cache_seconds: int = 30
    sql_echo: bool = False  # separate switch: SQL logging is too noisy for DEBUG

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Build Settings once and reuse it (lru_cache memoises the result)."""
    return Settings()


settings = get_settings()
