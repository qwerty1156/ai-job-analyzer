"""Celery-задача: выполняет анализ в фоне, сохраняет результат в PostgreSQL для владельца job."""

from app import models
from app.celery_app import celery_app
from app.db import SessionLocal
from app.exceptions import AppError
from app.services.analyzer import run_analysis


@celery_app.task(name="app.tasks.process_analysis_job", bind=True)
def process_analysis_job(self, job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(models.Job, job_id)
        if job is None:
            return

        job.status = "processing"
        db.commit()

        try:
            result = run_analysis(job.vacancy, job.skills)
        except AppError as exc:
            job.status = "failed"
            job.error_message = exc.message
            db.commit()
            return
        except Exception:
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
    finally:
        db.close()
