"""
Вызов LLM (Google Gemini) для анализа вакансии и резюме.

Почему Gemini, а не Anthropic API: у Anthropic нет постоянного
бесплатного тарифа (только платный pay-per-token), а у Google Gemini
API есть настоящий бесплатный тариф для моделей Flash/Flash-Lite через
Google AI Studio — без карты, с дневным лимитом запросов. Для пет-проекта
и портфолио это то, что нужно; при желании легко переключиться обратно —
вся интеграция с провайдером изолирована в этом файле.

Ключевой принцип: LLM -> structured output -> Pydantic. Мы просим Gemini
вернуть ответ строго по JSON Schema, сгенерированной из Pydantic-модели
(response_mime_type="application/json", response_schema=<PydanticModel>),
и SDK сам возвращает уже распарсенный и провалидированный объект
(response.parsed). Никакого ручного парсинга свободного текста.

Любая проблема на этом пути (нет ключа, таймаут, сетевая ошибка, лимит
запросов, невалидный ответ) превращается в понятное исключение из
app/exceptions.py и НЕ роняет процесс.
"""

import logging

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
from pydantic import ValidationError

from app.config import get_settings
from app.exceptions import (
    AIInvalidResponseError,
    AIRateLimitError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.schemas import AIAnalysisResult, MatchFacts, ResumeProfile
from app.services.prompts import (
    ANALYZE_SYSTEM_PROMPT,
    MATCH_SYSTEM_PROMPT,
    RESUME_SYSTEM_PROMPT,
    build_analyze_user_message,
    build_match_user_message,
    build_resume_user_message,
)

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    settings = get_settings()
    if not settings.AI_API_KEY:
        raise AIServiceUnavailableError(
            "AI_API_KEY не задан. Добавьте ключ Gemini API в .env, чтобы включить AI-анализ."
        )
    # timeout у google-genai задаётся в миллисекундах через http_options
    timeout_ms = int(settings.AI_TIMEOUT_SECONDS * 1000)
    return genai.Client(
        api_key=settings.AI_API_KEY,
        http_options=genai_types.HttpOptions(timeout=timeout_ms),
    )


def _generate_structured(
    system_prompt: str, user_message: str, response_schema: type, *, operation: str
) -> object:
    """
    Общая обёртка над вызовом Gemini с structured output.
    Возвращает уже распарсенный Pydantic-объект нужного типа (response_schema).

    operation — только для логов ("analyze"/"resume_profile"/"match_facts"),
    само содержимое запроса (текст вакансии/резюме) в логи не попадает.
    """
    settings = get_settings()
    client = _get_client()

    logger.info(
        "AI analysis started: operation=%s provider=gemini model=%s", operation, settings.AI_MODEL
    )

    try:
        response = client.models.generate_content(
            model=settings.AI_MODEL,
            contents=user_message,
            config=genai_types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2,
            ),
        )
    except genai_errors.ClientError as exc:
        status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
        message = str(exc)
        if status == 429 or "RESOURCE_EXHAUSTED" in message.upper():
            logger.warning("AI request failed: operation=%s reason=rate_limit", operation)
            raise AIRateLimitError(
                "Превышен лимит запросов к AI-сервису (бесплатный тариф Gemini). Попробуйте позже."
            ) from exc
        logger.error("AI request failed: operation=%s reason=client_error", operation)
        raise AIServiceUnavailableError(
            "AI-сервис отклонил запрос. Проверьте AI_API_KEY/AI_MODEL в конфигурации."
        ) from exc
    except genai_errors.ServerError as exc:
        logger.error("AI request failed: operation=%s reason=server_error", operation)
        raise AIServiceUnavailableError("AI-сервис временно недоступен. Попробуйте позже.") from exc
    except TimeoutError as exc:
        logger.warning("AI request failed: operation=%s reason=timeout", operation)
        raise AITimeoutError("AI-сервис не ответил за отведённое время. Попробуйте ещё раз.") from exc
    except genai_errors.APIError as exc:
        # Любая другая ошибка на уровне API, не подошедшая под Client/Server —
        # трактуем консервативно как недоступность, чтобы не падать с 500.
        logger.error("AI request failed: operation=%s reason=api_error", operation)
        raise AIServiceUnavailableError("AI-сервис вернул ошибку. Попробуйте позже.") from exc
    except Exception as exc:  # сетевые сбои httpx/сокетов и т.п.
        logger.error("AI request failed: operation=%s reason=network_error", operation)
        raise AIServiceUnavailableError("Не удалось подключиться к AI-сервису. Попробуйте позже.") from exc

    parsed = getattr(response, "parsed", None)
    if parsed is None:
        logger.error("AI request failed: operation=%s reason=no_structured_output", operation)
        raise AIInvalidResponseError("AI не вернул структурированный результат в ожидаемом формате.")

    try:
        # response.parsed уже является экземпляром response_schema в актуальных
        # версиях google-genai; на случай если пришёл dict — валидируем сами.
        if isinstance(parsed, response_schema):
            validated = parsed
        else:
            validated = response_schema.model_validate(parsed)
    except ValidationError as exc:
        logger.error("AI request failed: operation=%s reason=invalid_schema", operation)
        raise AIInvalidResponseError("AI вернул данные, не соответствующие ожидаемой структуре.") from exc

    logger.info("AI analysis completed: operation=%s", operation)
    return validated


def analyze_with_ai(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    """POST /analyze: вакансия + список навыков -> структурированный разбор соответствия."""
    user_message = build_analyze_user_message(vacancy, skills)
    return _generate_structured(ANALYZE_SYSTEM_PROMPT, user_message, AIAnalysisResult, operation="analyze")


def extract_resume_profile(resume_text: str) -> ResumeProfile:
    """POST /resume: текст резюме -> навыки/опыт/образование."""
    user_message = build_resume_user_message(resume_text)
    return _generate_structured(
        RESUME_SYSTEM_PROMPT, user_message, ResumeProfile, operation="resume_profile"
    )


def extract_match_facts(
    resume_skills: list[str], resume_experience: str, resume_education: str, vacancy: str
) -> MatchFacts:
    """POST /match: резюме + вакансия -> факты соответствия (без итогового процента)."""
    user_message = build_match_user_message(resume_skills, resume_experience, resume_education, vacancy)
    return _generate_structured(MATCH_SYSTEM_PROMPT, user_message, MatchFacts, operation="match_facts")
