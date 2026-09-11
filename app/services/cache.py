"""
Redis-кэш результатов анализа.

Идея: одинаковая вакансия + одинаковые навыки не должны каждый раз
уходить в AI заново. Ключ строится из нормализованных vacancy+skills,
значение — сериализованный AIAnalysisResult с TTL.

Redis рассматривается как необязательная оптимизация: если он
недоступен (сеть, не поднят локально и т.п.), сервис просто работает
без кэша — degradation, а не падение.
"""

import hashlib
import json
import logging

import redis

from app.config import get_settings
from app.schemas import AIAnalysisResult

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_client_url: str | None = None


def _get_client() -> redis.Redis | None:
    """Ленивая инициализация клиента; пересоздаётся, если REDIS_URL поменялся (тесты)."""
    global _client, _client_url
    settings = get_settings()
    if not settings.REDIS_URL:
        return None
    if _client is None or _client_url != settings.REDIS_URL:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
        _client_url = settings.REDIS_URL
    return _client


def _build_key(vacancy: str, skills: list[str]) -> str:
    normalized = json.dumps(
        {"vacancy": vacancy.strip(), "skills": sorted(s.strip().lower() for s in skills if s.strip())},
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"analysis:{digest}"


def get_cached(vacancy: str, skills: list[str]) -> AIAnalysisResult | None:
    """Возвращает закэшированный результат или None (в т.ч. если Redis недоступен)."""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_build_key(vacancy, skills))
    except redis.RedisError as exc:
        logger.warning("Redis недоступен при чтении кэша, продолжаем без кэша: %s", exc)
        return None

    if raw is None:
        return None

    try:
        return AIAnalysisResult.model_validate_json(raw)
    except Exception:  # повреждённая/устаревшая запись в кэше — просто игнорируем
        logger.warning("Повреждённая запись в кэше по ключу %s, игнорируем.", _build_key(vacancy, skills))
        return None


def set_cached(vacancy: str, skills: list[str], result: AIAnalysisResult) -> None:
    """Сохраняет результат в кэш с TTL. Ошибки Redis не должны ронять запрос."""
    client = _get_client()
    if client is None:
        return
    settings = get_settings()
    try:
        client.set(_build_key(vacancy, skills), result.model_dump_json(), ex=settings.CACHE_TTL_SECONDS)
    except redis.RedisError as exc:
        logger.warning("Redis недоступен при записи в кэш: %s", exc)
