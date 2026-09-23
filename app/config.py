"""
Конфигурация приложения.

Все настройки читаются из переменных окружения (.env). Никаких
API-ключей, паролей БД и секретов JWT в коде — только через os.getenv().
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


class Settings:
    """Простой контейнер настроек приложения."""

    # Общие настройки приложения
    APP_NAME: str = os.getenv("APP_NAME", "AI Job Analyzer")
    APP_VERSION: str = os.getenv("APP_VERSION", "0.3.0")
    DEBUG: bool = _get_bool("DEBUG", True)

    # --- AI-провайдер --------------------------------------------------
    # AI_PROVIDER=none    -> keyword-логика без AI (по умолчанию, без ключей)
    # AI_PROVIDER=gemini  -> реальный LLM-анализ через Google Gemini API
    #
    # Anthropic API — платный (без постоянного free-тарифа), поэтому по
    # умолчанию используется Google Gemini: у него есть настоящий
    # бесплатный тариф (модели Flash/Flash-Lite через Google AI Studio).
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "none")
    AI_API_KEY: str | None = os.getenv("AI_API_KEY")
    AI_MODEL: str = os.getenv("AI_MODEL", "gemini-2.5-flash")
    AI_TIMEOUT_SECONDS: float = float(os.getenv("AI_TIMEOUT_SECONDS", "30"))
    AI_MAX_RETRIES: int = _get_int("AI_MAX_RETRIES", 1)

    # Ограничения на вход, чтобы не улетали гигантские/пустые запросы в AI
    MIN_VACANCY_LENGTH: int = _get_int("MIN_VACANCY_LENGTH", 10)
    MAX_VACANCY_LENGTH: int = _get_int("MAX_VACANCY_LENGTH", 8000)
    MAX_RESUME_SIZE_MB: int = _get_int("MAX_RESUME_SIZE_MB", 5)

    # --- База данных (Этап 8) -------------------------------------------
        DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_analyzer",
    )

    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL[len("postgresql://"):]

    # --- Redis / кэш (Этап 10) ------------------------------------------
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CACHE_TTL_SECONDS: int = _get_int("CACHE_TTL_SECONDS", 3600)

    # --- Celery (Этап 11) ------------------------------------------------
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    # --- Авторизация / JWT (Этап 12) -------------------------------------
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-only-insecure-secret-change-me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = _get_int("JWT_EXPIRE_MINUTES", 60 * 24)

    # CORS
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")


@lru_cache
def get_settings() -> Settings:
    """Возвращает закэшированный экземпляр настроек (singleton на процесс)."""
    return Settings()
