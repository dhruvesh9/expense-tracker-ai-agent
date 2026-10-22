from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm: str = "openai"   # which provider to use: openai | gemini (each provider reads its own settings)
    backend_url: str = "http://localhost:8001/api/v1"
    history_db: str = "history.db"


@lru_cache  # build Settings once, then reuse the same object
def get_settings() -> Settings:
    return Settings()
