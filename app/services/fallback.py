"""
Fallback-анализ без AI.

Используется, когда settings.AI_PROVIDER == "none" (по умолчанию,
удобно для локальной разработки и тестов без API-ключа). Это та же
keyword-based логика, что была на Этапе 2, только приведённая к
формату AIAnalysisResult, чтобы analyzer.py мог одинаково работать
и с AI, и без него.
"""

import re

from app.schemas import AIAnalysisResult, MatchFacts, ResumeProfile

KNOWN_TECHNOLOGIES: list[str] = [
    "python", "java", "kotlin", "go", "golang", "rust", "c++", "c#",
    "javascript", "typescript", "node.js", "nodejs",
    "fastapi", "django", "flask", "spring", "express",
    "react", "vue", "angular", "next.js",
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis",
    "elasticsearch", "clickhouse",
    "docker", "kubernetes", "k8s", "terraform", "ansible",
    "aws", "gcp", "azure",
    "git", "github", "gitlab", "ci/cd", "jenkins",
    "rabbitmq", "kafka", "celery",
    "rest", "rest api", "graphql", "grpc", "websocket",
    "nginx", "linux",
    "pytest", "unittest",
    "sql", "nosql",
    "html", "css",
    "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn",
]


def _extract_requirements(vacancy_text: str) -> list[str]:
    text_lower = vacancy_text.lower()
    found: list[str] = []
    seen: set[str] = set()

    for tech in KNOWN_TECHNOLOGIES:
        if re.search(r"[^a-z0-9]", tech):
            match = tech in text_lower
        else:
            match = re.search(rf"\b{re.escape(tech)}\b", text_lower) is not None

        if match and tech not in seen:
            seen.add(tech)
            found.append(tech)

    return found


def _normalize_skills(skills: list[str]) -> set[str]:
    return {skill.strip().lower() for skill in skills if skill.strip()}


def analyze_stub(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    """Простое сопоставление по словарю технологий, без обращения к LLM."""
    requirements = _extract_requirements(vacancy)
    candidate_skills = _normalize_skills(skills)

    matched = [req for req in requirements if req in candidate_skills]
    missing = [req for req in requirements if req not in candidate_skills]

    match_percent = round(len(matched) / len(requirements) * 100) if requirements else 0

    summary = (
        f"[Режим без AI] В вакансии распознано требований: {len(requirements)}. "
        f"Закрыто навыками кандидата: {len(matched)}, не хватает: {len(missing)}."
    )

    return AIAnalysisResult(
        match_percent=match_percent,
        matched_skills=matched,
        missing_skills=missing,
        recommendations=[f"Изучить {tech}" for tech in missing],
        summary=summary,
    )


def extract_resume_profile_stub(resume_text: str) -> ResumeProfile:
    """Fallback для POST /resume: навыки — по словарю технологий, без AI."""
    skills = _extract_requirements(resume_text)
    return ResumeProfile(
        skills=skills,
        experience_summary="[Режим без AI] Автоматическое извлечение опыта недоступно без AI_PROVIDER.",
        education="",
    )


def extract_match_facts_stub(
    resume_skills: list[str], resume_experience: str, resume_education: str, vacancy: str
) -> MatchFacts:
    """Fallback для POST /match: те же эвристики по словарю, без AI."""
    requirements = _extract_requirements(vacancy)
    candidate_skills = _normalize_skills(resume_skills)

    matched = [req for req in requirements if req in candidate_skills]
    missing = [req for req in requirements if req not in candidate_skills]

    skills_score = (len(matched) / len(requirements)) if requirements else 0.0

    return MatchFacts(
        matched_skills=matched,
        missing_skills=missing,
        experience_gaps=[] if resume_experience else ["Опыт в резюме не указан"],
        skills_score=round(skills_score, 2),
        experience_score=0.5 if resume_experience else 0.0,
        education_score=0.5 if resume_education else 0.0,
        tools_score=round(skills_score, 2),
        other_score=0.5,
        summary=(
            f"[Режим без AI] Найдено требований в вакансии: {len(requirements)}, "
            f"закрыто резюме: {len(matched)}."
        ),
    )
