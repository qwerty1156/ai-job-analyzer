"""
Middleware, логирующее каждый HTTP-запрос: получение и завершение.

Намеренно НЕ логирует:
    - тело запроса (в /login и /register там пароль);
    - заголовки (в Authorization — Bearer-токен);
    - query-параметры (на случай, если туда когда-нибудь попадёт токен).

Логирует только метод, путь, итоговый статус и длительность — этого
достаточно, чтобы разбирать инциденты и мониторить производительность.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        start = time.monotonic()

        logger.info("request received: id=%s %s %s", request_id, request.method, request.url.path)

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "request failed: id=%s %s %s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "request completed: id=%s %s %s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
