"""POST /analyze — ставит анализ в очередь и сразу отвечает 202 Accepted."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AnalyzeRequest, JobAccepted
from app.services.analyzer import enqueue_analysis

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=JobAccepted, status_code=status.HTTP_202_ACCEPTED)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> JobAccepted:
    job = enqueue_analysis(db, payload.vacancy, payload.skills)
    return JobAccepted(job_id=job.id, status=job.status)
