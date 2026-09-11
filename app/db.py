"""
Подключение к PostgreSQL через SQLAlchemy.

Используется современный psycopg (v3) как драйвер:
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

Для боевого проекта миграции лучше вести через Alembic; здесь для
простоты используется Base.metadata.create_all() при старте приложения
(см. app/main.py, startup-хук init_db()).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


def get_db():
    """FastAPI-зависимость: сессия БД на время запроса, всегда закрывается."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Создаёт таблицы, если их ещё нет. Вызывается при старте приложения."""
    from app import models  # noqa: F401  регистрирует модели в Base.metadata

    Base.metadata.create_all(bind=engine)
