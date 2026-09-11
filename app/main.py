"""Точка входа FastAPI-приложения AI Job Analyzer."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.analyses import router as analyses_router
from app.api.analyze import router as analyze_router
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.match import router as match_router
from app.api.resume import router as resume_router
from app.config import get_settings
from app.db import init_db
from app.exceptions import AppError
from app.logging_config import setup_logging
from app.middleware import RequestLoggingMiddleware

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(jobs_router)
app.include_router(analyses_router)
app.include_router(resume_router)
app.include_router(match_router)


@app.on_event("startup")
def on_startup() -> None:
    try:
        init_db()
    except Exception:
        logger.exception("Не удалось инициализировать БД при старте приложения")


@app.get("/")
def health_check() -> dict:
    """Простой health-check эндпоинт."""
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    logger.warning("AppError %s on %s: %s", exc.error_code, request.url.path, exc.message)
    return JSONResponse(status_code=exc.status_code, content={"error": exc.error_code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Pydantic кладёт исходное невалидное значение в "input" — для password
    # при /register это был бы сам пароль. Вырезаем его перед логом и ответом.
    sanitized_errors = [{k: v for k, v in e.items() if k != "input"} for e in exc.errors()]
    logger.info("Validation error on %s: %s", request.url.path, sanitized_errors)
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request", "message": "Некорректные входные данные.", "details": sanitized_errors},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"error": "internal_error", "message": "Внутренняя ошибка сервера."})
