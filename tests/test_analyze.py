from unittest.mock import patch

from app import models

VALID_PAYLOAD = {
    "vacancy": (
        "Ищем Python Backend Developer. Требования: Python, FastAPI, PostgreSQL, Docker."
    ),
    "skills": ["Python", "FastAPI", "PostgreSQL"],
}


def test_analyze_requires_auth(client):
    response = client.post("/analyze", json=VALID_PAYLOAD)
    assert response.status_code == 401


def test_analyze_empty_vacancy_returns_400_without_enqueueing(client, auth_headers):
    with patch("app.tasks.process_analysis_job.delay") as mock_delay:
        response = client.post("/analyze", json={"vacancy": "", "skills": ["Python"]}, headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"
    mock_delay.assert_not_called()


def test_analyze_empty_skills_returns_400(client, auth_headers):
    response = client.post(
        "/analyze",
        json={"vacancy": "Ищем Python Backend Developer с опытом FastAPI.", "skills": []},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_analyze_valid_request_returns_202_and_creates_job(client, auth_headers, user, db_session):
    with patch("app.tasks.process_analysis_job.delay") as mock_delay:
        response = client.post("/analyze", json=VALID_PAYLOAD, headers=auth_headers)

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "pending"
    assert "job_id" in data

    job = db_session.get(models.Job, data["job_id"])
    assert job is not None
    assert job.user_id == user.id
    assert job.status == "pending"
    mock_delay.assert_called_once_with(job.id)


def test_get_job_requires_auth(client):
    response = client.get("/jobs/does-not-exist")
    assert response.status_code == 401


def test_get_job_not_found_returns_404(client, auth_headers):
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


def test_get_job_belonging_to_other_user_returns_404(client, auth_headers, other_auth_headers):
    with patch("app.tasks.process_analysis_job.delay"):
        create_response = client.post("/analyze", json=VALID_PAYLOAD, headers=auth_headers)
    job_id = create_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}", headers=other_auth_headers)
    assert response.status_code == 404


def test_get_job_pending_right_after_creation(client, auth_headers):
    with patch("app.tasks.process_analysis_job.delay"):
        create_response = client.post("/analyze", json=VALID_PAYLOAD, headers=auth_headers)
    job_id = create_response.json()["job_id"]

    response = client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["analysis"] is None
