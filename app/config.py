from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    google_api_key: str = ""
    redis_url: str = "redis://127.0.0.1:6379"
    session_db_url: str = "sqlite+aiosqlite:///./data/sessions.sqlite"
    poc_db_url: str = "sqlite+aiosqlite:///./data/poc.sqlite"
    queue_name: str = "fastapi-adk-messages"
    buffer_ms: float = 0.4
    port: int = 8000
    embed_worker: bool = True

    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_app_secret: str = ""
    whatsapp_app_id: str = ""
    whatsapp_agent_id: str = "amaru"

    @property
    def whatsapp_configured(self) -> bool:
        return bool(self.whatsapp_token and self.whatsapp_phone_number_id and self.whatsapp_verify_token)


@lru_cache
def get_settings() -> Settings:
    return Settings()
