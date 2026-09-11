"""Pydantic-схемы запроса/ответа."""

from datetime import datetime

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    vacancy: str = Field(..., min_length=1)
    skills: list[str] = Field(default_factory=list)


class AIAnalysisResult(BaseModel):
    match_percent: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str


class AnalyzeResponse(AIAnalysisResult):
    model_config = {"from_attributes": True}


class AnalysisListItem(BaseModel):
    id: int
    match_percent: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(BaseModel):
    id: int
    vacancy: str
    skills: list[str]
    match_percent: int
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[str]
    summary: str
    created_at: datetime

    model_config = {"from_attributes": True}


class JobAccepted(BaseModel):
    job_id: str
    status: str = "pending"


class JobStatusResponse(BaseModel):
    id: str
    status: str
    analysis: AnalysisDetail | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
