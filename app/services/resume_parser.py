"""
Извлечение и очистка текста резюме из PDF/DOCX (Этап 13).

PDF/DOCX -> extract text -> clean text -> (дальше в services/resume.py: AI -> skills -> database)
"""

import io

import docx
from pypdf import PdfReader

from app.exceptions import InvalidRequestError

_PDF_CONTENT_TYPES = {"application/pdf"}
_DOCX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def extract_text(file_bytes: bytes, content_type: str | None, filename: str) -> str:
    """
    Определяет тип файла (по content_type, с фолбэком на расширение),
    извлекает текст и очищает его. Бросает InvalidRequestError (400) на
    неподдерживаемый формат, пустой или нечитаемый файл.
    """
    kind = _detect_kind(content_type, filename)

    if kind == "pdf":
        raw_text = _extract_pdf(file_bytes)
    else:
        raw_text = _extract_docx(file_bytes)

    cleaned = _clean_text(raw_text)
    if not cleaned:
        raise InvalidRequestError(
            "Не удалось извлечь текст из резюме — файл пустой, повреждён или это скан без текстового слоя."
        )
    return cleaned


def _detect_kind(content_type: str | None, filename: str) -> str:
    if content_type in _PDF_CONTENT_TYPES:
        return "pdf"
    if content_type in _DOCX_CONTENT_TYPES:
        return "docx"

    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        return "pdf"
    if lower_name.endswith(".docx"):
        return "docx"

    raise InvalidRequestError("Поддерживаются только файлы резюме в форматах PDF и DOCX.")


def _extract_pdf(file_bytes: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise InvalidRequestError("Не удалось прочитать PDF-файл — возможно, он повреждён.") from exc


def _extract_docx(file_bytes: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise InvalidRequestError("Не удалось прочитать DOCX-файл — возможно, он повреждён.") from exc


def _clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines).strip()
