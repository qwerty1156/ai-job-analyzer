"""Роут POST /analyze — тонкий, вся логика в app/services/analyzer.py."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyze_vacancy

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, db: Session = Depends(get_db)) -> AnalyzeResponse:
    analysis = analyze_vacancy(db, payload.vacancy, payload.skills)
    return AnalyzeResponse.model_validate(analysis)
