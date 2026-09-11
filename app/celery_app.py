"""Celery-приложение для фоновой обработки анализов."""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery("ai_job_analyzer", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"])
celery_app.autodiscover_tasks(["app"])
