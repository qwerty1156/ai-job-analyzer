"""
Общие фикстуры для тестов.

БД: используется SQLite in-memory вместо реального PostgreSQL — тесты
не требуют поднятой инфраструктуры (docker compose) и работают быстро.
get_db переопределяется через app.dependency_overrides.

Celery: process_analysis_job.delay мокается в тестах, которые его
касаются (test_analyze_job.py) — реальный Redis-брокер не нужен.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.db import Base, get_db
from app.deps import get_current_user
from app.main import app
from app.services.security import create_access_token, hash_password

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _fresh_schema():
    """Пересоздаёт схему БД перед каждым тестом — тесты полностью изолированы друг от друга."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def user(db_session):
    """Создаёт тестового пользователя напрямую в БД (без похода через /register)."""
    u = models.User(email="test@example.com", hashed_password=hash_password("password123"))
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def other_user(db_session):
    u = models.User(email="other@example.com", hashed_password=hash_password("password123"))
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def auth_headers(user):
    token = create_access_token(user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user):
    token = create_access_token(other_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def current_user_override(user):
    """Альтернатива auth_headers: подменяет get_current_user напрямую (без JWT в заголовках)."""
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    del app.dependency_overrides[get_current_user]
