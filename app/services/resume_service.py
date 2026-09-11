"""
Бизнес-логика загрузки резюме (Этап 13).

    PDF/DOCX -> extract text -> clean text -> AI (или fallback) -> skills -> database
"""

import logging

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.exceptions import InvalidRequestError
from app.schemas import ResumeProfile
from app.services import ai as ai_service
from app.services import fallback
from app.services.resume_parser import extract_text

logger = logging.getLogger(__name__)


def process_resume_upload(
    db: Session, user: models.User, file_bytes: bytes, content_type: str | None, filename: str
) -> models.Resume:
    """Полный пайплайн: валидация -> извлечение текста -> AI/fallback -> сохранение в БД."""
    settings = get_settings()

    max_bytes = settings.MAX_RESUME_SIZE_MB * 1024 * 1024
    if len(file_bytes) == 0:
        raise InvalidRequestError("Файл резюме пустой.")
    if len(file_bytes) > max_bytes:
        raise InvalidRequestError(f"Файл резюме слишком большой (максимум {settings.MAX_RESUME_SIZE_MB} МБ).")

    cleaned_text = extract_text(file_bytes, content_type, filename)

    profile: ResumeProfile
    if settings.AI_PROVIDER == "none":
        profile = fallback.extract_resume_profile_stub(cleaned_text)
    else:
        profile = ai_service.extract_resume_profile(cleaned_text)

    resume = models.Resume(
        user_id=user.id,
        filename=filename,
        raw_text=cleaned_text,
        skills=profile.skills,
        experience_summary=profile.experience_summary or None,
        education=profile.education or None,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume
