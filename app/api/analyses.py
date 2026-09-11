"""GET /analyses и GET /analyses/{id} — история анализов."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.db import get_db
from app.schemas import AnalysisDetail, AnalysisListItem

router = APIRouter(tags=["analyses"])


@router.get("/analyses", response_model=list[AnalysisListItem])
def list_analyses(db: Session = Depends(get_db)) -> list[models.Analysis]:
    return db.query(models.Analysis).order_by(models.Analysis.created_at.desc()).all()


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
def get_analysis(analysis_id: int, db: Session = Depends(get_db)) -> models.Analysis:
    analysis = db.get(models.Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Анализ не найден.")
    return analysis
