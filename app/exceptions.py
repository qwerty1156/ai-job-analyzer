"""
Кастомные исключения приложения.

Каждое исключение знает свой HTTP-статус — обработчики в app/main.py
превращают их в корректный JSON-ответ, не давая приложению падать
из-за одного плохого запроса или сбоя внешнего AI-сервиса.

Маппинг:
    InvalidRequestError      -> 400  неправильные входные данные
    AuthError                 -> 401  нет/невалиден токен авторизации
    ForbiddenError            -> 403  нет прав на этот ресурс
    NotFoundError              -> 404  ресурс не найден
    ConflictError              -> 409  конфликт (например, email уже занят)
    AIRateLimitError         -> 429  слишком много запросов к AI
    AIServiceUnavailableError-> 503  AI-сервис недоступен / не ответил
    AITimeoutError            -> 503  таймаут запроса к AI (частный случай unavailable)
    AIInvalidResponseError   -> 500  AI ответил, но не тем, что нужно
    InternalError             -> 500  любая другая внутренняя ошибка
"""


class AppError(Exception):
    """Базовый класс для ошибок приложения, которые превращаются в HTTP-ответ."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidRequestError(AppError):
    """Некорректные входные данные: пустая/слишком длинная вакансия, пустой skills и т.п."""

    status_code = 400
    error_code = "invalid_request"


class AuthError(AppError):
    """Нет токена, токен невалиден/истёк, или неверный логин/пароль."""

    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    """Пользователь аутентифицирован, но не имеет прав на этот ресурс."""

    status_code = 403
    error_code = "forbidden"


class NotFoundError(AppError):
    """Запрошенный ресурс не найден (или не принадлежит текущему пользователю)."""

    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    """Конфликт состояния, например регистрация с уже занятым email."""

    status_code = 409
    error_code = "conflict"


class AIRateLimitError(AppError):
    """AI-провайдер вернул 429 — превышен лимит запросов."""

    status_code = 429
    error_code = "ai_rate_limited"


class AIServiceUnavailableError(AppError):
    """AI-провайдер недоступен: сетевая ошибка, 5xx, нет ключа и т.п."""

    status_code = 503
    error_code = "ai_service_unavailable"


class AITimeoutError(AIServiceUnavailableError):
    """AI не ответил за отведённое время. Частный случай недоступности."""

    error_code = "ai_timeout"


class AIInvalidResponseError(AppError):
    """AI вернул ответ, который не удалось разобрать в ожидаемую структуру."""

    status_code = 500
    error_code = "ai_invalid_response"


class InternalError(AppError):
    """Любая другая непредвиденная внутренняя ошибка."""

    status_code = 500
    error_code = "internal_error"
