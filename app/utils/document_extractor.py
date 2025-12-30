import os
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def _read_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            parts.append(p.text)
    return "\n".join(parts)


def extract_text(file_path: str, file_type: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(file_path)

    ft = (file_type or "").lower().lstrip(".")
    if not ft:
        ft = os.path.splitext(path.name)[1].lower().lstrip(".")

    if ft in {"txt", "md"}:
        return _read_txt(path)
    if ft == "pdf":
        return _read_pdf(path)
    if ft in {"docx"}:
        return _read_docx(path)

    raise ValueError(f"Unsupported file type: {file_type}")
