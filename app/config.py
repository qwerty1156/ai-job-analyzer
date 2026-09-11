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

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_analyzer"
    )

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()
