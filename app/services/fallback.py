"""Keyword-based fallback анализ без AI (используется при AI_PROVIDER=none)."""

from app.schemas import AIAnalysisResult

KNOWN_TECHNOLOGIES = ["python", "fastapi", "postgresql", "docker", "sql", "git"]


def analyze_stub(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    vacancy_lower = vacancy.lower()
    candidate_skills = {s.strip().lower() for s in skills}

    required = [tech for tech in KNOWN_TECHNOLOGIES if tech in vacancy_lower]
    matched = [tech for tech in required if tech in candidate_skills]
    missing = [tech for tech in required if tech not in candidate_skills]
    match_percent = round(len(matched) / len(required) * 100) if required else 0

    return AIAnalysisResult(
        match_percent=match_percent,
        matched_skills=matched,
        missing_skills=missing,
        recommendations=[f"Изучить {tech}" for tech in missing],
        summary=f"[Без AI] Закрыто {len(matched)} из {len(required)} требований.",
    )
