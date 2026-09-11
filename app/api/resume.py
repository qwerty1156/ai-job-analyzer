"""POST /resume — загрузка PDF/DOCX резюме (Этап 13)."""

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.schemas import ResumeOut
from app.services.resume_service import process_resume_upload

router = APIRouter(tags=["resume"])


@router.post(
    "/resume",
    response_model=ResumeOut,
    status_code=201,
    summary="Загрузить резюме (PDF или DOCX)",
    description="Извлекает текст из файла, очищает его и передаёт AI (или встроенной "
    "keyword-эвристике при `AI_PROVIDER=none`) для распознавания навыков, краткого опыта и "
    "образования. Возвращает сохранённое резюме — используйте `resume.id` в `POST /match`. "
    "Максимальный размер файла — `MAX_RESUME_SIZE_MB` (по умолчанию 5 МБ).",
)
async def upload_resume(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> models.Resume:
    file_bytes = await file.read()
    return process_resume_upload(
        db=db,
        user=user,
        file_bytes=file_bytes,
        content_type=file.content_type,
        filename=file.filename or "resume",
    )
