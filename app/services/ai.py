"""
Вызов LLM (Anthropic Claude) для анализа вакансии.

Принцип: LLM -> structured output -> Pydantic. Модель обязана вызвать
инструмент submit_analysis со схемой, сгенерированной из AIAnalysisResult —
никакого парсинга свободного текста регулярками.
"""

import anthropic

from app.config import get_settings
from app.schemas import AIAnalysisResult

TOOL_NAME = "submit_analysis"

_ANALYSIS_TOOL = {
    "name": TOOL_NAME,
    "description": "Отправить структурированный результат анализа соответствия кандидата вакансии.",
    "input_schema": AIAnalysisResult.model_json_schema(),
}


def analyze_with_ai(vacancy: str, skills: list[str]) -> AIAnalysisResult:
    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.AI_API_KEY)

    response = client.messages.create(
        model=settings.AI_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": f"Вакансия:\n{vacancy}\n\nНавыки: {skills}"}],
        tools=[_ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": TOOL_NAME},
    )

    tool_use = next(b for b in response.content if b.type == "tool_use")
    return AIAnalysisResult.model_validate(tool_use.input)
