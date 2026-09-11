"""POST /match — резюме против вакансии, с собственным scoring engine (Этапы 14-15)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models
from app.deps import get_current_user, get_db
from app.schemas import MatchRequest, MatchResponse
from app.services.matching import match_resume_to_vacancy

router = APIRouter(tags=["match"])


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Сопоставить резюме с вакансией",
    description="Берёт ранее загруженное резюме (`resume_id` из `POST /resume`) и текст "
    "вакансии. AI извлекает только факты (покрытие по навыкам/опыту/образованию/инструментам/"
    "прочему, 0.0–1.0 каждое) — итоговый `match_percent` считает backend по прозрачной "
    "взвешенной формуле (см. `score_breakdown` в ответе). Результат сохраняется в историю.",
)
def match(
    payload: MatchRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> MatchResponse:
    return match_resume_to_vacancy(db, user, payload.resume_id, payload.vacancy)
