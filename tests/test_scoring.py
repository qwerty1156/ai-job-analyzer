import pytest

from app.services.scoring import DEFAULT_WEIGHTS, ScoringFacts, compute_match_score


def test_compute_match_score_default_weights():
    facts = ScoringFacts(
        skills_score=1.0, experience_score=1.0, education_score=1.0, tools_score=1.0, other_score=1.0
    )
    result = compute_match_score(facts)
    assert result["match_percent"] == 100
    assert result["weights"] == DEFAULT_WEIGHTS


def test_compute_match_score_zero_facts():
    facts = ScoringFacts(
        skills_score=0.0, experience_score=0.0, education_score=0.0, tools_score=0.0, other_score=0.0
    )
    result = compute_match_score(facts)
    assert result["match_percent"] == 0


def test_compute_match_score_skills_weighted_most():
    # Только skills=1.0, всё остальное 0 -> итог должен быть равен весу skills (50%)
    facts = ScoringFacts(
        skills_score=1.0, experience_score=0.0, education_score=0.0, tools_score=0.0, other_score=0.0
    )
    result = compute_match_score(facts)
    assert result["match_percent"] == 50


def test_compute_match_score_clamps_out_of_range_values():
    facts = ScoringFacts(
        skills_score=1.5,  # AI могла ошибиться и прислать > 1 — не должно ломать формулу
        experience_score=-0.2,
        education_score=0.5,
        tools_score=0.5,
        other_score=0.5,
    )
    result = compute_match_score(facts)
    assert 0 <= result["match_percent"] <= 100
    assert result["components"]["skills"] == 1.0
    assert result["components"]["experience"] == 0.0


def test_compute_match_score_rejects_invalid_weights():
    facts = ScoringFacts(
        skills_score=0.5, experience_score=0.5, education_score=0.5, tools_score=0.5, other_score=0.5
    )
    with pytest.raises(ValueError):
        compute_match_score(facts, weights={"skills": 0.9, "experience": 0.9})
