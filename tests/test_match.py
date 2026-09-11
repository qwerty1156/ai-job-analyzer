from unittest.mock import patch

import pytest

from app import models
from app.config import get_settings
from app.exceptions import AIInvalidResponseError, AIRateLimitError, AIServiceUnavailableError
from app.schemas import MatchFacts


def _make_resume(db_session, user, skills=None):
    resume = models.Resume(
        user_id=user.id,
        filename="resume.docx",
        raw_text="Python FastAPI PostgreSQL developer.",
        skills=skills if skills is not None else ["python", "fastapi", "postgresql"],
        experience_summary="4 года опыта backend-разработки.",
        education="Бакалавр компьютерных наук.",
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


VACANCY = "Ищем Python Backend Developer. Требования: Python, FastAPI, PostgreSQL, Docker."


def test_match_requires_auth(client):
    response = client.post("/match", json={"resume_id": 1, "vacancy": VACANCY})
    assert response.status_code == 401


def test_match_resume_not_found_returns_404(client, auth_headers):
    response = client.post("/match", json={"resume_id": 999999, "vacancy": VACANCY}, headers=auth_headers)
    assert response.status_code == 404


def test_match_other_users_resume_returns_404(client, db_session, other_user, auth_headers):
    resume = _make_resume(db_session, other_user)
    response = client.post(
        "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
    )
    assert response.status_code == 404


def test_match_fallback_without_ai_uses_scoring_engine(client, db_session, user, auth_headers):
    resume = _make_resume(db_session, user)

    response = client.post(
        "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()

    # 3 из 4 требований вакансии (python/fastapi/postgresql) закрыты резюме -> skills_score = 0.75
    # match_percent считает backend (scoring engine), а не AI — проверяем именно формулу.
    assert data["score_breakdown"]["components"]["skills"] == 0.75
    assert data["match_percent"] == data["score_breakdown"]["match_percent"]
    assert "docker" in data["missing_skills"]

    # результат должен сохраниться в историю анализов
    history = client.get("/analyses", headers=auth_headers)
    assert len(history.json()) == 1


def test_match_empty_vacancy_returns_400(client, db_session, user, auth_headers):
    resume = _make_resume(db_session, user)
    response = client.post("/match", json={"resume_id": resume.id, "vacancy": ""}, headers=auth_headers)
    assert response.status_code == 400


@pytest.fixture
def ai_mode():
    settings = get_settings()
    original = settings.AI_PROVIDER
    settings.AI_PROVIDER = "gemini"
    yield settings
    settings.AI_PROVIDER = original


def test_match_ai_success(client, db_session, user, auth_headers, ai_mode):
    resume = _make_resume(db_session, user)
    fake_facts = MatchFacts(
        matched_skills=["Python", "FastAPI"],
        missing_skills=["Docker"],
        experience_gaps=[],
        skills_score=0.75,
        experience_score=0.8,
        education_score=1.0,
        tools_score=0.5,
        other_score=0.6,
        summary="Кандидат хорошо подходит.",
    )
    with patch("app.services.matching.ai_service.extract_match_facts", return_value=fake_facts):
        response = client.post(
            "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
        )
    assert response.status_code == 200
    data = response.json()
    # 0.75*50 + 0.8*20 + 1.0*10 + 0.5*10 + 0.6*10 = 37.5+16+10+5+6 = 74.5 -> round -> 75 (округление .5 к чётному в Python round())
    assert data["match_percent"] in (74, 75)


def test_match_ai_rate_limit_returns_429(client, db_session, user, auth_headers, ai_mode):
    resume = _make_resume(db_session, user)
    with patch(
        "app.services.matching.ai_service.extract_match_facts",
        side_effect=AIRateLimitError("Превышен лимит запросов."),
    ):
        response = client.post(
            "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
        )
    assert response.status_code == 429
    assert response.json()["error"] == "ai_rate_limited"


def test_match_ai_unavailable_returns_503(client, db_session, user, auth_headers, ai_mode):
    resume = _make_resume(db_session, user)
    with patch(
        "app.services.matching.ai_service.extract_match_facts",
        side_effect=AIServiceUnavailableError("AI-сервис недоступен."),
    ):
        response = client.post(
            "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
        )
    assert response.status_code == 503


def test_match_ai_invalid_response_returns_500(client, db_session, user, auth_headers, ai_mode):
    resume = _make_resume(db_session, user)
    with patch(
        "app.services.matching.ai_service.extract_match_facts",
        side_effect=AIInvalidResponseError("AI вернул невалидный формат."),
    ):
        response = client.post(
            "/match", json={"resume_id": resume.id, "vacancy": VACANCY}, headers=auth_headers
        )
    assert response.status_code == 500
