"""
POST /analyze (Этапы 3, 6, 10, 11, 12).

Тонкий endpoint: ставит анализ в очередь на фоновую обработку и сразу
отвечает 202 Accepted. Результат доступен через GET /jobs/{job_id},
как только Celery-воркер его посчитает (с учётом Redis-кэша).
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.schemas import AnalyzeRequest, JobAccepted
from app.services.analyzer import enqueue_analysis

router = APIRouter(tags=["analyze"])


@router.post(
    "/analyze",
    response_model=JobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Поставить анализ вакансии в очередь на фоновую обработку",
)
def analyze(
    payload: AnalyzeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> JobAccepted:
    job = enqueue_analysis(db, user, payload.vacancy, payload.skills)
    return JobAccepted(job_id=job.id, status=job.status)
