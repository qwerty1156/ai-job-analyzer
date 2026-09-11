"""
Бизнес-логика POST /match (Этапы 14-15): резюме против вакансии.

    AI -> extraction (факты по 5 измерениям, 0.0-1.0 каждое)
    Backend -> decision (итоговый match_percent считает scoring engine,
               а не AI)
"""

import logging

from sqlalchemy.orm import Session

from app import models
from app.config import get_settings
from app.exceptions import InvalidRequestError, NotFoundError
from app.schemas import MatchFacts, MatchResponse
from app.services import ai as ai_service
from app.services import fallback
from app.services.scoring import ScoringFacts, compute_match_score

logger = logging.getLogger(__name__)


def match_resume_to_vacancy(db: Session, user: models.User, resume_id: int, vacancy: str) -> MatchResponse:
    resume = db.get(models.Resume, resume_id)
    if resume is None or resume.user_id != user.id:
        raise NotFoundError("Резюме не найдено.")

    clean_vacancy = vacancy.strip()
    settings = get_settings()

    if not clean_vacancy:
        raise InvalidRequestError("Текст вакансии не может быть пустым.")
    if len(clean_vacancy) < settings.MIN_VACANCY_LENGTH:
        raise InvalidRequestError(
            f"Текст вакансии слишком короткий (минимум {settings.MIN_VACANCY_LENGTH} символов)."
        )
    if len(clean_vacancy) > settings.MAX_VACANCY_LENGTH:
        raise InvalidRequestError(
            f"Текст вакансии слишком длинный (максимум {settings.MAX_VACANCY_LENGTH} символов)."
        )
    if not resume.skills:
        raise InvalidRequestError(
            "У этого резюме не распознано ни одного навыка — сопоставление с вакансией невозможно."
        )

    facts: MatchFacts
    if settings.AI_PROVIDER == "none":
        facts = fallback.extract_match_facts_stub(
            resume.skills, resume.experience_summary or "", resume.education or "", clean_vacancy
        )
    else:
        facts = ai_service.extract_match_facts(
            resume.skills, resume.experience_summary or "", resume.education or "", clean_vacancy
        )

    scoring_facts = ScoringFacts(
        skills_score=facts.skills_score,
        experience_score=facts.experience_score,
        education_score=facts.education_score,
        tools_score=facts.tools_score,
        other_score=facts.other_score,
    )
    score = compute_match_score(scoring_facts)

    recommendations = [f"Изучить {skill}" for skill in facts.missing_skills] + [
        f"Закрыть пробел в опыте: {gap}" for gap in facts.experience_gaps
    ]

    response = MatchResponse(
        match_percent=score["match_percent"],
        matched_skills=facts.matched_skills,
        missing_skills=facts.missing_skills,
        experience_gaps=facts.experience_gaps,
        recommendations=recommendations,
        summary=facts.summary,
        score_breakdown=score,
    )

    # Сохраняем как Analysis для истории — с привязкой к резюме и разбивкой score.
    analysis = models.Analysis(
        user_id=user.id,
        resume_id=resume.id,
        vacancy=clean_vacancy,
        skills=resume.skills,
        match_percent=response.match_percent,
        matched_skills=response.matched_skills,
        missing_skills=response.missing_skills,
        recommendations=response.recommendations,
        summary=response.summary,
        experience_gaps=response.experience_gaps,
        score_breakdown=response.score_breakdown,
    )
    db.add(analysis)
    db.commit()

    return response
