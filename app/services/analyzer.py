"""
Бизнес-логика анализа вакансии.

    run_analysis()     — чистая функция: валидация -> Redis-кэш -> AI/fallback -> кэш.
                          Используется Celery-воркером.
    enqueue_analysis()  — создаёт Job и ставит фоновую задачу в очередь Celery;
                          вызывается из POST /analyze, который сразу отвечает 202.
"""

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.exceptions import InvalidRequestError
from app.schemas import AIAnalysisResult
from app.services import ai as ai_service
from app.services import cache, fallback

MIN_VACANCY_LENGTH = 10
MAX_VACANCY_LENGTH = 8000


def validate_vacancy_and_skills(vacancy: str, skills: list[str]) -> None:
    if not vacancy:
        raise InvalidRequestError("Текст вакансии не может быть пустым.")
    if len(vacancy) < MIN_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком короткий.")
    if len(vacancy) > MAX_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком длинный.")
    if not skills:
        raise InvalidRequestError("Список навыков не может быть пустым.")


def run_analysis(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    validate_vacancy_and_skills(vacancy, skills)
    settings = get_settings()

    cached = cache.get_cached(vacancy, skills)
    if cached is not None:
        return cached

    if settings.AI_PROVIDER == "none":
        result = fallback.analyze_stub(vacancy, skills)
    else:
        result = ai_service.analyze_with_ai(vacancy, skills)

    cache.set_cached(vacancy, skills, result)
    return result


def enqueue_analysis(db: Session, vacancy: str, skills: list[str]) -> models.Job:
    validate_vacancy_and_skills(vacancy, skills)

    from app.tasks import process_analysis_job

    job = models.Job(vacancy=vacancy, skills=skills, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_analysis_job.delay(job.id)
    return job
