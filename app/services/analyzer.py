"""
Бизнес-логика анализа вакансии.

    run_analysis()      — чистая функция: валидация -> Redis-кэш -> AI/fallback -> кэш.
                           Не знает ничего про FastAPI/HTTP/БД. Используется
                           Celery-воркером (app/tasks.py) для фактической обработки.

    enqueue_analysis()   — вызывается из FastAPI endpoint (POST /analyze):
                           валидирует вход, создаёт Job-запись в БД и ставит
                           фоновую Celery-задачу в очередь. Сразу возвращает
                           Job, endpoint отвечает 202 Accepted.

Архитектура:
    Request -> FastAPI endpoint -> enqueue_analysis() -> Job (БД) -> Celery
                                                                        ↓
                                                              run_analysis() -> Redis? -> AI/fallback
                                                                        ↓
                                                                  PostgreSQL (Analysis)
"""

import logging

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.exceptions import InvalidRequestError
from app.schemas import AIAnalysisResult
from app.services import ai as ai_service
from app.services import cache, fallback

logger = logging.getLogger(__name__)


def validate_vacancy_and_skills(vacancy: str, skills: list[str]) -> None:
    """Проверка входных данных до траты времени/денег на AI-запрос (Этап 6)."""
    settings = get_settings()

    if not vacancy:
        raise InvalidRequestError("Текст вакансии не может быть пустым.")
    if len(vacancy) < settings.MIN_VACANCY_LENGTH:
        raise InvalidRequestError(
            f"Текст вакансии слишком короткий (минимум {settings.MIN_VACANCY_LENGTH} символов)."
        )
    if len(vacancy) > settings.MAX_VACANCY_LENGTH:
        raise InvalidRequestError(
            f"Текст вакансии слишком длинный (максимум {settings.MAX_VACANCY_LENGTH} символов)."
        )
    if not skills:
        raise InvalidRequestError("Список навыков не может быть пустым — укажите хотя бы один навык.")


def run_analysis(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    """
    Чистая функция анализа (без FastAPI/БД): валидация -> кэш -> AI/fallback -> кэш.
    Вызывается из Celery-задачи (app/tasks.py::process_analysis_job).
    """
    validate_vacancy_and_skills(vacancy, skills)
    settings = get_settings()

    cached = cache.get_cached(vacancy, skills)
    if cached is not None:
        logger.info("Cache hit для анализа вакансии — AI не вызывается")
        return cached

    if settings.AI_PROVIDER == "none":
        result = fallback.analyze_stub(vacancy, skills)
    else:
        result = ai_service.analyze_with_ai(vacancy, skills)

    cache.set_cached(vacancy, skills, result)
    return result


def enqueue_analysis(db: Session, user: models.User, vacancy: str, skills: list[str]) -> models.Job:
    """
    Создаёт Job-запись и ставит фоновую задачу в очередь Celery.
    Валидация происходит здесь же, ДО создания Job — чтобы сразу вернуть
    400, а не создавать мусорную задачу под заведомо плохой запрос.
    """
    clean_vacancy = vacancy.strip()
    clean_skills = [s.strip() for s in skills if s.strip()]
    validate_vacancy_and_skills(clean_vacancy, clean_skills)

    from app.tasks import process_analysis_job  # локальный импорт: без цикла FastAPI<->Celery на старте

    job = models.Job(user_id=user.id, vacancy=clean_vacancy, skills=clean_skills, status="pending")
    db.add(job)
    db.commit()
    db.refresh(job)

    process_analysis_job.delay(job.id)
    logger.info("job queued: job_id=%s user_id=%s skills_count=%d", job.id, user.id, len(clean_skills))
    return job
