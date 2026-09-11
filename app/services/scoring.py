"""
Scoring engine (Этап 15).

Принцип: AI -> extraction, Backend -> decision.

AI (см. app/services/ai.py::extract_match_facts) извлекает ФАКТЫ:
насколько покрыты навыки, опыт, образование, инструменты и "прочее" —
каждое отдельным числом 0.0-1.0. Итоговый match_percent считает не AI,
а эта прозрачная взвешенная формула — так проценту можно доверять и
его можно объяснить пользователю (score_breakdown), а не гадать, что
там "решила" модель.
"""

from dataclasses import dataclass

DEFAULT_WEIGHTS: dict[str, float] = {
    "skills": 0.5,
    "experience": 0.2,
    "education": 0.1,
    "tools": 0.1,
    "other": 0.1,
}


@dataclass(frozen=True)
class ScoringFacts:
    """Факты, извлечённые AI (или fallback-эвристикой) — каждое поле 0.0-1.0."""

    skills_score: float
    experience_score: float
    education_score: float
    tools_score: float
    other_score: float


def compute_match_score(facts: ScoringFacts, weights: dict[str, float] | None = None) -> dict:
    """
    Считает итоговый match_percent по взвешенной формуле.

    Возвращает словарь с итоговым процентом, использованными весами и
    вкладом (0-100) каждого компонента — это и есть "score_breakdown",
    который видит пользователь и по которому можно объяснить результат.
    """
    weights = weights or DEFAULT_WEIGHTS
    _validate_weights(weights)

    components = {
        "skills": _clamp(facts.skills_score),
        "experience": _clamp(facts.experience_score),
        "education": _clamp(facts.education_score),
        "tools": _clamp(facts.tools_score),
        "other": _clamp(facts.other_score),
    }

    contributions = {key: round(components[key] * weights[key] * 100, 1) for key in weights}
    match_percent = round(sum(contributions.values()))
    match_percent = max(0, min(100, match_percent))

    return {
        "match_percent": match_percent,
        "weights": weights,
        "components": components,
        "contributions": contributions,
    }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _validate_weights(weights: dict[str, float]) -> None:
    total = sum(weights.values())
    if not (0.99 <= total <= 1.01):
        raise ValueError(f"Сумма весов scoring engine должна быть равна 1.0, получено {total}")
