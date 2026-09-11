"""GET /jobs/{id} — статус фоновой задачи анализа (Этап 11)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError
from app.schemas import AnalysisDetail, JobStatusResponse

router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Статус фоновой задачи анализа",
    description="Поллинг-эндпоинт для результата `POST /analyze`. `status` проходит "
    "`pending` → `processing` → `completed` (тогда заполнено поле `analysis`) или "
    "`failed` (тогда заполнено `error_message`). Доступна только своя задача — 404 на чужую.",
)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> JobStatusResponse:
    job = db.get(models.Job, job_id)
    if job is None or job.user_id != user.id:
        raise NotFoundError("Задача не найдена.")

    analysis = db.get(models.Analysis, job.analysis_id) if job.analysis_id is not None else None

    return JobStatusResponse(
        id=job.id,
        status=job.status,
        analysis=AnalysisDetail.model_validate(analysis) if analysis is not None else None,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
