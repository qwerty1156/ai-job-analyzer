"""Точка входа FastAPI-приложения AI Job Analyzer."""

from fastapi import FastAPI

from app.api.analyze import router as analyze_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.include_router(analyze_router)


@app.get("/")
def health_check() -> dict:
    """Простой health-check эндпоинт."""
    return {"status": "ok"}
