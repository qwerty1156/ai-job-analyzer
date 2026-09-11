"""Конфигурация приложения. Настройки читаются из .env."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AI Job Analyzer")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.1.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")

    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "none")
    AI_API_KEY: str | None = os.getenv("AI_API_KEY")
    AI_MODEL: str = os.getenv("AI_MODEL", "claude-sonnet-4-6")


@lru_cache
def get_settings() -> Settings:
    return Settings()
