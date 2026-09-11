import io

import docx

from app.config import get_settings


def _make_docx_bytes(text_lines: list[str]) -> bytes:
    document = docx.Document()
    for line in text_lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def test_upload_resume_requires_auth(client):
    file_bytes = _make_docx_bytes(["Python developer with FastAPI experience."])
    response = client.post(
        "/resume", files={"file": ("resume.docx", file_bytes, DOCX_CONTENT_TYPE)}
    )
    assert response.status_code == 401


def test_upload_resume_extracts_skills_without_ai(client, auth_headers, user):
    # AI_PROVIDER=none по умолчанию -> используется fallback (словарь технологий)
    file_bytes = _make_docx_bytes(
        [
            "Иван Иванов — Python Backend Developer",
            "Опыт: 4 года с Python, FastAPI, PostgreSQL и Docker.",
        ]
    )
    response = client.post(
        "/resume",
        files={"file": ("resume.docx", file_bytes, DOCX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "resume.docx"
    assert set(data["skills"]) >= {"python", "fastapi", "postgresql", "docker"}


def test_upload_resume_rejects_unsupported_format(client, auth_headers):
    response = client.post(
        "/resume",
        files={"file": ("resume.txt", b"just some text", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_request"


def test_upload_resume_rejects_empty_file(client, auth_headers):
    response = client.post(
        "/resume",
        files={"file": ("resume.docx", b"", DOCX_CONTENT_TYPE)},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_upload_resume_rejects_too_large_file(client, auth_headers):
    settings = get_settings()
    original = settings.MAX_RESUME_SIZE_MB
    settings.MAX_RESUME_SIZE_MB = 0  # любой ненулевой файл теперь "слишком большой"
    try:
        file_bytes = _make_docx_bytes(["Some content"])
        response = client.post(
            "/resume",
            files={"file": ("resume.docx", file_bytes, DOCX_CONTENT_TYPE)},
            headers=auth_headers,
        )
        assert response.status_code == 400
    finally:
        settings.MAX_RESUME_SIZE_MB = original
