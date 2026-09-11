"""POST /analyze — ставит анализ в очередь для текущего пользователя, 202 Accepted."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.schemas import AnalyzeRequest, JobAccepted
from app.services.analyzer import enqueue_analysis

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def analyze(
    payload: AnalyzeRequest, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
) -> JobAccepted:
    job = enqueue_analysis(db, user, payload.vacancy, payload.skills)
    return JobAccepted(job_id=job.id, status=job.status)
