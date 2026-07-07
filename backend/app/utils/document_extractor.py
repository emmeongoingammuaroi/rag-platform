"""Text extraction from uploaded files (PDF, DOCX, TXT, MD).

Phase 4.1: PyMuPDF for better PDF text, pdfplumber for table extraction.
Phase 4.2: OCR via pytesseract for scanned PDFs.
"""

import logging
import os
from pathlib import Path

import fitz
import pdfplumber
from docx import Document as DocxDocument

from app.core.config import settings

logger = logging.getLogger(__name__)


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _extract_tables_from_page(pdf_path: Path, page_num: int) -> str:
    """Extract tables from a specific PDF page using pdfplumber, formatted as markdown."""
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_num >= len(pdf.pages):
                return ""
            page = pdf.pages[page_num]
            tables = page.extract_tables()
            if not tables:
                return ""

            parts: list[str] = []
            for table in tables:
                if not table or not table[0]:
                    continue
                header = table[0]
                md_lines: list[str] = []
                md_lines.append("| " + " | ".join(cell or "" for cell in header) + " |")
                md_lines.append("| " + " | ".join("---" for _ in header) + " |")
                for row in table[1:]:
                    md_lines.append("| " + " | ".join(cell or "" for cell in row) + " |")
                parts.append("\n".join(md_lines))
            return "\n\n".join(parts)
    except Exception as e:
        logger.debug(f"Table extraction failed for page {page_num}: {e}")
        return ""


def _is_scanned_page(page: fitz.Page, min_text_length: int = 30) -> bool:
    """Detect if a page is scanned (image-only with little/no extractable text)."""
    text = page.get_text("text").strip()
    return len(text) < min_text_length and len(page.get_images()) > 0


def _ocr_page(page: fitz.Page) -> str:
    """Run OCR on a scanned PDF page via pytesseract."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract or Pillow not installed, skipping OCR")
        return ""

    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text: str = pytesseract.image_to_string(img, lang=settings.OCR_LANGUAGE)
    return text.strip()


def _read_pdf(path: Path) -> str:
    """Extract text from PDF using PyMuPDF + pdfplumber tables + optional OCR."""
    doc = fitz.open(str(path))
    parts: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").strip()

        if _is_scanned_page(page) and settings.OCR_ENABLED:
            ocr_text = _ocr_page(page)
            if ocr_text:
                text = ocr_text

        table_md = _extract_tables_from_page(path, page_num)

        page_parts: list[str] = []
        if text:
            page_parts.append(text)
        if table_md:
            page_parts.append(table_md)

        if page_parts:
            parts.append("\n\n".join(page_parts))

    doc.close()
    return "\n\n".join(parts)


def _read_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text and p.text.strip():
            parts.append(p.text)
    return "\n".join(parts)


def extract_text(file_path: str, file_type: str) -> str:
    """Extract text content from a local file path.

    Args:
        file_path: Path to the file on disk.
        file_type: File extension (pdf, docx, txt, md).

    Returns:
        Extracted text content.

    Raises:
        FileNotFoundError: If file does not exist.
        ValueError: If file type is unsupported.
    """
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


def extract_text_from_bytes(data: bytes, file_type: str) -> str:
    """Extract text from in-memory bytes (downloaded from object storage).

    Writes to a temp file then delegates to the type-specific extractor.

    Args:
        data: Raw file bytes.
        file_type: File extension (pdf, docx, txt, md).

    Returns:
        Extracted text content.

    Raises:
        ValueError: If file type is unsupported.
    """
    import tempfile

    ft = (file_type or "").lower().lstrip(".")

    if ft in {"txt", "md"}:
        return data.decode("utf-8", errors="ignore")

    with tempfile.NamedTemporaryFile(suffix=f".{ft}", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        path = Path(tmp.name)
        if ft == "pdf":
            return _read_pdf(path)
        if ft == "docx":
            return _read_docx(path)

    raise ValueError(f"Unsupported file type: {file_type}")
