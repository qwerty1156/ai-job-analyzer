"""FastAPI-зависимости: сессия БД и текущий авторизованный пользователь."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.exceptions import AuthError
from app.services.security import decode_access_token

# tokenUrl используется только для описания в Swagger ("Authorize" -> Bearer).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """Достаёт пользователя из Bearer JWT-токена. Бросает AuthError (401), если что-то не так."""
    if not token:
        raise AuthError("Требуется авторизация: передайте заголовок Authorization: Bearer <token>.")

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (PyJWTError, KeyError, ValueError) as exc:
        raise AuthError("Невалидный или истёкший токен авторизации.") from exc

    user = db.get(models.User, user_id)
    if user is None:
        raise AuthError("Пользователь из токена не найден.")

    return user
