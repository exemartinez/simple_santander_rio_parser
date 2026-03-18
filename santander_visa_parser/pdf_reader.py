"""PDF reading helpers for Santander Visa statements."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_text_from_pdf(path: Path) -> str:
    """Return the concatenated text extracted from all pages of a PDF file."""
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)

