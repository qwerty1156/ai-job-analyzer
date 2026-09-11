"""Сервисный слой: валидация -> AI/fallback -> результат."""

from app.config import get_settings
from app.exceptions import InvalidRequestError
from app.services import ai as ai_service
from app.services import fallback

MIN_VACANCY_LENGTH = 10
MAX_VACANCY_LENGTH = 8000


def _validate(vacancy: str, skills: list[str]) -> None:
    if not vacancy:
        raise InvalidRequestError("Текст вакансии не может быть пустым.")
    if len(vacancy) < MIN_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком короткий.")
    if len(vacancy) > MAX_VACANCY_LENGTH:
        raise InvalidRequestError("Текст вакансии слишком длинный.")
    if not skills:
        raise InvalidRequestError("Список навыков не может быть пустым.")


def analyze_vacancy(vacancy: str, skills: list[str]) -> dict:
    _validate(vacancy, skills)
    settings = get_settings()

    if settings.AI_PROVIDER == "none":
        result = fallback.analyze_stub(vacancy, skills)
    else:
        result = ai_service.analyze_with_ai(vacancy, skills)

    return result.model_dump()
