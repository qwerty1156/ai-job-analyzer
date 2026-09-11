"""
Celery-задачи.

process_analysis_job — выполняется в воркере, а не в веб-процессе:
запускает run_analysis() (кэш -> AI/fallback), сохраняет результат
как Analysis в PostgreSQL и обновляет статус Job (pending -> processing
-> completed/failed). Веб-процесс никогда не блокируется на AI-запросе.
"""

import logging

from app import models
from app.celery_app import celery_app
from app.db import SessionLocal
from app.exceptions import AppError
from app.services.analyzer import run_analysis

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.process_analysis_job", bind=True, max_retries=2, default_retry_delay=5)
def process_analysis_job(self, job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(models.Job, job_id)
        if job is None:
            logger.error("Job %s не найден в БД, пропускаем.", job_id)
            return

        job.status = "processing"
        db.commit()
        logger.info("job processing started: job_id=%s user_id=%s", job_id, job.user_id)

        try:
            result = run_analysis(job.vacancy, job.skills)
        except AppError as exc:
            # Доменная ошибка (AI недоступен, лимит и т.п.) — фиксируем как failed,
            # не роняем воркер и не делаем бесконечные ретраи на плохом входе.
            logger.warning("job failed: job_id=%s reason=%s", job_id, exc.error_code)
            job.status = "failed"
            job.error_message = exc.message
            db.commit()
            return
        except Exception:  # noqa: BLE001 — последний рубеж, воркер не должен падать
            logger.exception("job failed: job_id=%s reason=unexpected_error", job_id)
            job.status = "failed"
            job.error_message = "Внутренняя ошибка при обработке анализа."
            db.commit()
            return

        analysis = models.Analysis(
            user_id=job.user_id,
            vacancy=job.vacancy,
            skills=job.skills,
            match_percent=result.match_percent,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
            recommendations=result.recommendations,
            summary=result.summary,
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        job.status = "completed"
        job.analysis_id = analysis.id
        db.commit()
        logger.info("job completed: job_id=%s analysis_id=%s", job_id, analysis.id)
    finally:
        db.close()
