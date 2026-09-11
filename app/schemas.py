"""Pydantic-схемы запроса/ответа."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    vacancy: str = Field(..., min_length=1)
    skills: list[str] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    """Строго структурированный результат анализа, который обязан вернуть LLM."""

    match_percent: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str


class AnalyzeResponse(AIAnalysisResult):
    pass
