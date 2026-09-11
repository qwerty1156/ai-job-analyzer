"""Роут POST /analyze. Пока с временной (не-AI) логикой прямо в эндпоинте."""

from fastapi import APIRouter

from app.schemas import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])

KNOWN_TECHNOLOGIES = ["python", "fastapi", "postgresql", "docker", "sql", "git"]


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_vacancy(payload: AnalyzeRequest) -> AnalyzeResponse:
    vacancy_lower = payload.vacancy.lower()
    candidate_skills = {s.strip().lower() for s in payload.skills}

    required = [tech for tech in KNOWN_TECHNOLOGIES if tech in vacancy_lower]
    matched = [tech for tech in required if tech in candidate_skills]
    missing = [tech for tech in required if tech not in candidate_skills]

    match_percent = round(len(matched) / len(required) * 100) if required else 0

    return AnalyzeResponse(match_percent=match_percent, matched=matched, missing=missing)
