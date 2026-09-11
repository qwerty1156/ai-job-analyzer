"""GET /analyses и GET /analyses/{id} — история анализов текущего пользователя."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError
from app.schemas import AnalysisDetail, AnalysisListItem

router = APIRouter(tags=["analyses"])


@router.get("/analyses", response_model=list[AnalysisListItem])
def list_analyses(
    db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
) -> list[models.Analysis]:
    return (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == user.id)
        .order_by(models.Analysis.created_at.desc())
        .all()
    )


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(
    analysis_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)
) -> models.Analysis:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise NotFoundError("Анализ не найден.")
    return analysis
