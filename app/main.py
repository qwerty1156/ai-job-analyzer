"""Точка входа FastAPI-приложения AI Job Analyzer."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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

OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Регистрация, вход и получение данных текущего пользователя. Все остальные "
        "эндпоинты (кроме health-check) требуют JWT из `POST /login` в заголовке "
        "`Authorization: Bearer <token>`.",
    },
    {
        "name": "analyze",
        "description": "Постановка анализа вакансии (по списку навыков) в фоновую очередь. "
        "Отвечает `202 Accepted` сразу же — результат нужно забирать через `GET /jobs/{id}`.",
    },
    {
        "name": "jobs",
        "description": "Статус фоновых задач анализа: `pending` → `processing` → `completed`/`failed`.",
    },
    {
        "name": "analyses",
        "description": "История уже завершённых анализов текущего пользователя (по навыкам и по резюме).",
    },
    {
        "name": "resume",
        "description": "Загрузка резюме (PDF/DOCX): текст извлекается, очищается и передаётся AI "
        "(или встроенной эвристике) для распознавания навыков, опыта и образования.",
    },
    {
        "name": "match",
        "description": "Сопоставление ранее загруженного резюме с текстом вакансии. Итоговый процент "
        "считает backend по прозрачной формуле (scoring engine), AI только извлекает факты.",
    },
    {
        "name": "system",
        "description": "Служебные эндпоинты (health-check).",
    },
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Backend-сервис, который принимает вакансию и резюме/навыки пользователя и оценивает, "
        "насколько кандидат ей подходит.\n\n"
        "**Быстрый старт**: `POST /register` → `POST /login` (получить `access_token`) → "
        "любой из эндпоинтов ниже с заголовком `Authorization: Bearer <access_token>`."
    ),
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth_router)
app.include_router(analyze_router)
app.include_router(jobs_router)
app.include_router(analyses_router)
app.include_router(resume_router)
app.include_router(match_router)


@app.on_event("startup")
def on_startup() -> None:
    """Создаёт таблицы в PostgreSQL, если их ещё нет (см. app/db.py::init_db)."""
    try:
        init_db()
    except Exception:
        # Не роняем процесс, если БД временно недоступна на старте (например,
        # контейнер Postgres ещё поднимается) — но громко логируем.
        logger.exception("Не удалось инициализировать БД при старте приложения")


@app.get("/", tags=["system"], summary="Health-check")
def health_check() -> dict:
    """Простой health-check эндпоинт — не требует авторизации."""
    return {"status": "ok"}


# --- Централизованная обработка ошибок ---------------------------------
# Ни одно необработанное исключение (наше или чужое) не должно ронять
# процесс или отдавать голый traceback наружу.


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Все наши доменные исключения (app/exceptions.py) -> корректный HTTP-ответ."""
    logger.warning("AppError %s on %s: %s", exc.error_code, request.url.path, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error_code, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Невалидный по схеме запрос (например, skills не список) -> 400, а не 422-стектрейс.

    ВАЖНО: Pydantic включает в каждую ошибку поле "input" — фактическое значение,
    которое не прошло валидацию. Для /register и /login это может быть пароль!
    Поэтому "input" всегда вырезается перед тем, как ошибка попадёт в лог или
    в ответ клиенту — иначе короткий/невалидный пароль утёк бы в логи как есть.
    """
    sanitized_errors = [
        {key: value for key, value in error.items() if key != "input"} for error in exc.errors()
    ]
    logger.info("Validation error on %s: %s", request.url.path, sanitized_errors)
    return JSONResponse(
        status_code=400,
        content={
            "error": "invalid_request",
            "message": "Некорректные входные данные.",
            "details": sanitized_errors,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Последний рубеж: любая непредвиденная ошибка -> 500, а не падение процесса."""
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Произошла внутренняя ошибка сервера."},
    )
