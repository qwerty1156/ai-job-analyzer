"""POST /register, POST /login, GET /me (Этап 12)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.exceptions import AuthError, ConflictError
from app.schemas import LoginRequest, Token, UserCreate, UserOut
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="Зарегистрировать нового пользователя",
    description="Создаёт пользователя по email и паролю (минимум 8 символов). "
    "Пароль хранится только в виде bcrypt-хэша. Возвращает 409, если email уже занят.",
)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing is not None:
        raise ConflictError("Пользователь с таким email уже зарегистрирован.")

    user = models.User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=Token,
    summary="Войти и получить JWT",
    description="Проверяет email/пароль и возвращает `access_token` (Bearer JWT, живёт "
    "`JWT_EXPIRE_MINUTES`). Передавайте его во всех остальных запросах в заголовке "
    "`Authorization: Bearer <access_token>`.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AuthError("Неверный email или пароль.")

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Текущий пользователь",
    description="Возвращает профиль пользователя, которому принадлежит переданный Bearer-токен.",
)
def me(user: models.User = Depends(get_current_user)) -> UserOut:
    return user
