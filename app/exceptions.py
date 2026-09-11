"""Доменные исключения, которые превращаются в корректные HTTP-ответы."""


class AppError(Exception):
    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class InvalidRequestError(AppError):
    status_code = 400
    error_code = "invalid_request"


class AIRateLimitError(AppError):
    status_code = 429
    error_code = "ai_rate_limited"


class AIServiceUnavailableError(AppError):
    status_code = 503
    error_code = "ai_service_unavailable"


class AITimeoutError(AIServiceUnavailableError):
    error_code = "ai_timeout"


class AIInvalidResponseError(AppError):
    status_code = 500
    error_code = "ai_invalid_response"


class AuthError(AppError):
    status_code = 401
    error_code = "unauthorized"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"
