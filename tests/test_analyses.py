from app import models


def _make_analysis(db_session, user, match_percent=75, resume_id=None):
    analysis = models.Analysis(
        user_id=user.id,
        resume_id=resume_id,
        vacancy="Ищем Python Backend Developer.",
        skills=["python", "fastapi"],
        match_percent=match_percent,
        matched_skills=["python"],
        missing_skills=["docker"],
        recommendations=["Изучить docker"],
        summary="Тестовый анализ.",
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)
    return analysis


def test_list_analyses_requires_auth(client):
    response = client.get("/analyses")
    assert response.status_code == 401


def test_list_analyses_empty_for_new_user(client, auth_headers):
    response = client.get("/analyses", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_list_analyses_returns_only_current_user_summaries(client, db_session, user, other_user, auth_headers):
    _make_analysis(db_session, user, match_percent=75)
    _make_analysis(db_session, user, match_percent=40)
    _make_analysis(db_session, other_user, match_percent=99)  # чужой анализ — не должен попасть в список

    response = client.get("/analyses", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert {item["match_percent"] for item in data} == {75, 40}
    # список должен быть только сводкой (id, match_percent, created_at) — без полного текста вакансии
    assert "vacancy" not in data[0]


def test_get_analysis_detail(client, db_session, user, auth_headers):
    analysis = _make_analysis(db_session, user)

    response = client.get(f"/analyses/{analysis.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis.id
    assert data["vacancy"] == analysis.vacancy
    assert data["matched_skills"] == ["python"]


def test_get_analysis_not_found(client, auth_headers):
    response = client.get("/analyses/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_analysis_belonging_to_other_user_returns_404(client, db_session, other_user, auth_headers):
    analysis = _make_analysis(db_session, other_user)

    response = client.get(f"/analyses/{analysis.id}", headers=auth_headers)
    assert response.status_code == 404
