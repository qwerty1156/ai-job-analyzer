"""Точка входа FastAPI-приложения AI Job Analyzer."""

from fastapi import FastAPI

from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


@app.get("/")
def health_check() -> dict:
    """Простой health-check эндпоинт."""
    return {"status": "ok"}
