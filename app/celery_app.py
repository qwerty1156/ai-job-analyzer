"""
Celery-приложение для фоновой обработки анализов (Этап 11).

Запуск воркера:
    celery -A app.celery_app worker --loglevel=info
"""

from celery import Celery

from app.config import get_settings
from app.db import init_db

settings = get_settings()

# Воркер тоже должен быть уверен, что таблицы существуют (на случай, если
# он поднимается раньше/без веб-процесса) — create_all идемпотентен.
try:
    init_db()
except Exception:  # БД может быть временно недоступна — не роняем импорт модуля
    pass

celery_app = Celery(
    "ai_job_analyzer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
)

# Регистрирует задачи из app/tasks.py при старте воркера.
celery_app.autodiscover_tasks(["app"])
