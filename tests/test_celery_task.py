"""
Проверяет app/tasks.py::process_analysis_job без реального Celery-брокера:
task.apply() выполняет задачу синхронно, в текущем процессе. SessionLocal
внутри tasks.py подменяется на тестовую (SQLite), чтобы не трогать
реальный PostgreSQL.
"""

from unittest.mock import patch

from app import models
from tests.conftest import TestingSessionLocal


def test_process_analysis_job_completes_and_saves_analysis(monkeypatch, db_session, user):
    import app.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "SessionLocal", TestingSessionLocal)

    job = models.Job(
        user_id=user.id,
        vacancy="Ищем Python Backend Developer. Требования: Python, FastAPI, PostgreSQL, Docker.",
        skills=["Python", "FastAPI", "PostgreSQL"],
        status="pending",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    result = tasks_module.process_analysis_job.apply(args=(job.id,))
    assert result.successful()

    db_session.refresh(job)
    assert job.status == "completed"
    assert job.analysis_id is not None

    analysis = db_session.get(models.Analysis, job.analysis_id)
    assert analysis is not None
    assert analysis.user_id == user.id
    assert set(analysis.matched_skills) == {"python", "fastapi", "postgresql"}
    assert analysis.missing_skills == ["docker"]
    assert analysis.match_percent == 75


def test_process_analysis_job_missing_job_is_noop(monkeypatch):
    import app.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "SessionLocal", TestingSessionLocal)

    result = tasks_module.process_analysis_job.apply(args=("00000000-0000-0000-0000-000000000000",))
    assert result.successful()


def test_process_analysis_job_ai_failure_marks_job_failed(monkeypatch, db_session, user):
    """Ошибка AI (например, недоступен сервис) не должна ронять воркер —
    job помечается failed с человекочитаемым error_message."""
    import app.tasks as tasks_module
    from app.config import get_settings
    from app.exceptions import AIServiceUnavailableError

    monkeypatch.setattr(tasks_module, "SessionLocal", TestingSessionLocal)

    settings = get_settings()
    original_provider = settings.AI_PROVIDER
    settings.AI_PROVIDER = "gemini"

    job = models.Job(
        user_id=user.id,
        vacancy="Ищем Python Backend Developer с опытом FastAPI.",
        skills=["Python"],
        status="pending",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    try:
        with patch(
            "app.services.analyzer.ai_service.analyze_with_ai",
            side_effect=AIServiceUnavailableError("AI-сервис недоступен."),
        ):
            result = tasks_module.process_analysis_job.apply(args=(job.id,))
    finally:
        settings.AI_PROVIDER = original_provider

    assert result.successful()  # сама Celery-задача не падает

    db_session.refresh(job)
    assert job.status == "failed"
    assert job.error_message == "AI-сервис недоступен."
    assert job.analysis_id is None
