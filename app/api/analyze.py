"""Роут POST /analyze — тонкий, вся логика в app/services/analyzer.py."""

from fastapi import APIRouter

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.analyzer import analyze_vacancy

router = APIRouter(tags=["analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest) -> AnalyzeResponse:
    result = analyze_vacancy(payload.vacancy, payload.skills)
    return AnalyzeResponse(**result)
