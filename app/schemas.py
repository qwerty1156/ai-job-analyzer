"""
Pydantic-схемы.

AIAnalysisResult — единый структурированный формат, который обязан
вернуть LLM (через structured output), без произвольного текста и
парсинга регулярками — сразу валидируется этим же Pydantic.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# --- Анализ вакансии (Этапы 2-11) ---------------------------------------


class AnalyzeRequest(BaseModel):
    """Входные данные: текст вакансии и список навыков кандидата."""

    vacancy: str = Field(
        ...,
        description="Текст вакансии целиком (описание, требования и т.д.)",
        examples=["Ищем Python Backend Developer со знанием FastAPI и PostgreSQL"],
    )
    skills: list[str] = Field(
        default_factory=list,
        description="Список навыков/технологий кандидата",
        examples=[["Python", "FastAPI", "PostgreSQL", "Docker"]],
    )


class AIAnalysisResult(BaseModel):
    """Строго структурированный результат анализа — форма, которую обязан вернуть LLM."""

    match_percent: int = Field(..., ge=0, le=100)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str


class JobAccepted(BaseModel):
    """Ответ на POST /analyze — задача поставлена в очередь (202 Accepted)."""

    job_id: str
    status: str = "pending"


class AnalysisListItem(BaseModel):
    """Элемент списка GET /analyses — только сводка, без полного текста вакансии."""

    id: int
    match_percent: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(BaseModel):
    """Полная запись анализа — GET /analyses/{id} и вложенный результат job'ы."""

    id: int
    vacancy: str
    skills: list[str]
    match_percent: int
    matched_skills: list[str]
    missing_skills: list[str]
    recommendations: list[str]
    summary: str
    experience_gaps: list[str] | None = None
    score_breakdown: dict | None = None
    resume_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobStatusResponse(BaseModel):
    """Ответ GET /jobs/{id}."""

    id: str
    status: str  # pending | processing | completed | failed
    analysis: AnalysisDetail | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# --- Авторизация (Этап 12) ----------------------------------------------


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Минимум 8 символов")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Резюме (Этап 13) -----------------------------------------------------


class ResumeProfile(BaseModel):
    """Структурированный результат извлечения фактов из резюме (LLM или fallback)."""

    skills: list[str] = Field(default_factory=list)
    experience_summary: str = Field(default="")
    education: str = Field(default="")


class ResumeOut(BaseModel):
    id: int
    filename: str
    skills: list[str]
    experience_summary: str | None = None
    education: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Match: резюме против вакансии (Этапы 14-15) --------------------------


class MatchRequest(BaseModel):
    resume_id: int
    vacancy: str


class MatchFacts(BaseModel):
    """
    Факты, которые извлекает AI. AI НЕ считает итоговый процент —
    он оценивает степень покрытия по каждому измерению (0.0-1.0),
    а финальный match_percent считает backend (см. services/scoring.py).
    """

    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    experience_gaps: list[str] = Field(default_factory=list)

    skills_score: float = Field(..., ge=0, le=1, description="Покрытие требуемых навыков, 0-1")
    experience_score: float = Field(..., ge=0, le=1, description="Соответствие по опыту, 0-1")
    education_score: float = Field(..., ge=0, le=1, description="Соответствие по образованию, 0-1")
    tools_score: float = Field(..., ge=0, le=1, description="Покрытие инструментов/тулинга, 0-1")
    other_score: float = Field(..., ge=0, le=1, description="Прочие факторы (soft skills и т.п.), 0-1")

    summary: str


class MatchResponse(BaseModel):
    match_percent: int
    matched_skills: list[str]
    missing_skills: list[str]
    experience_gaps: list[str]
    recommendations: list[str]
    summary: str
    score_breakdown: dict


# --- Общий формат ошибок ---------------------------------------------------


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Код ошибки, например ai_rate_limited")
    message: str = Field(..., description="Человекочитаемое описание ошибки")
