"""Сервисный слой: валидация -> Redis-кэш -> AI/fallback -> PostgreSQL -> результат."""

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.exceptions import InvalidRequestError
from app.services import ai as ai_service
from app.services import cache, fallback

MIN_VACANCY_LENGTH = 10
MAX_VACANCY_LENGTH = 8000


def _validate(vacancy: str, skills: list[str]) -> None:
    if not vacancy:
        raise InvalidRequestError("Текст вакансии не может быть пустым.")
    if len(vacancy) < MIN_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком короткий.")
    if len(vacancy) > MAX_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком длинный.")
    if not skills:
        raise InvalidRequestError("Список навыков не может быть пустым.")


def analyze_vacancy(db: Session, vacancy: str, skills: list[str]) -> models.Analysis:
    _validate(vacancy, skills)
    settings = get_settings()

    result = cache.get_cached(vacancy, skills)
    if result is None:
        if settings.AI_PROVIDER == "none":
            result = fallback.analyze_stub(vacancy, skills)
        else:
            result = ai_service.analyze_with_ai(vacancy, skills)
        cache.set_cached(vacancy, skills, result)

    analysis = models.Analysis(
        vacancy=vacancy,
        skills=skills,
        match_percent=result.match_percent,
        matched_skills=result.matched_skills,
        missing_skills=result.missing_skills,
        recommendations=result.recommendations,
        summary=result.summary,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis
