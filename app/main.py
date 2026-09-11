"""Точка входа FastAPI-приложения AI Job Analyzer."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.analyze import router as analyze_router
from app.config import get_settings
from app.exceptions import AppError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.include_router(analyze_router)


@app.get("/")
def health_check() -> dict:
    """Простой health-check эндпоинт."""
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error_code, "message": exc.message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": "Внутренняя ошибка."})
