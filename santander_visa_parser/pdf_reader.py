"""Object-oriented PDF reading helpers."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


class PDFTextReader:
    """Read text content from PDF files."""

    def extract_text(self, path: Path) -> str:
        """Return the concatenated text extracted from all pages of a PDF file."""
        reader = PdfReader(str(path))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
