"""ORM-модели."""

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    vacancy: Mapped[str] = mapped_column(Text, nullable=False)
    skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    match_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    recommendations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
