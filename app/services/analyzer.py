"""Сервисный слой бизнес-логики анализа вакансии."""

from app.services import ai as ai_service


def analyze_vacancy(vacancy: str, skills: list[str]) -> dict:
    """Request -> Service -> AI -> Result."""
    result = ai_service.analyze_with_ai(vacancy, skills)
    return result.model_dump()
