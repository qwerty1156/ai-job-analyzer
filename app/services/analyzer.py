"""Сервисный слой бизнес-логики анализа вакансии."""

KNOWN_TECHNOLOGIES = ["python", "fastapi", "postgresql", "docker", "sql", "git"]


def analyze_vacancy(vacancy: str, skills: list[str]) -> dict:
    """Request -> Service -> Result. Пока временная (не-AI) логика сопоставления."""
    vacancy_lower = vacancy.lower()
    candidate_skills = {s.strip().lower() for s in skills}

    required = [tech for tech in KNOWN_TECHNOLOGIES if tech in vacancy_lower]
    matched = [tech for tech in required if tech in candidate_skills]
    missing = [tech for tech in required if tech not in candidate_skills]

    match_percent = round(len(matched) / len(required) * 100) if required else 0

    return {"match_percent": match_percent, "matched": matched, "missing": missing}
