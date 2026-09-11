"""Redis-кэш результатов анализа: одинаковая вакансия+навыки не должны каждый раз уходить в AI."""

import hashlib
import json
import logging

import redis

from app.config import get_settings
from app.schemas import AIAnalysisResult

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def _get_client() -> redis.Redis | None:
    global _client
    settings = get_settings()
    if not settings.REDIS_URL:
        return None
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True, socket_timeout=2)
    return _client


def _build_key(vacancy: str, skills: list[str]) -> str:
    normalized = json.dumps({"vacancy": vacancy.strip(), "skills": sorted(s.lower() for s in skills)})
    return "analysis:" + hashlib.sha256(normalized.encode()).hexdigest()


def get_cached(vacancy: str, skills: list[str]) -> AIAnalysisResult | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(_build_key(vacancy, skills))
    except redis.RedisError as exc:
        logger.warning("Redis недоступен при чтении кэша: %s", exc)
        return None
    return AIAnalysisResult.model_validate_json(raw) if raw else None


def set_cached(vacancy: str, skills: list[str], result: AIAnalysisResult) -> None:
    client = _get_client()
    if client is None:
        return
    settings = get_settings()
    try:
        client.set(_build_key(vacancy, skills), result.model_dump_json(), ex=settings.CACHE_TTL_SECONDS)
    except redis.RedisError as exc:
        logger.warning("Redis недоступен при записи в кэш: %s", exc)
