"""Pydantic-схемы запроса/ответа для эндпоинта /analyze."""

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    vacancy: str = Field(..., min_length=1)
    skills: list[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    match_percent: int = Field(..., ge=0, le=100)
    matched: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
