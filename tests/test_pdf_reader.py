from __future__ import annotations

from pathlib import Path

from santander_visa_parser import pdf_reader
from santander_visa_parser.pdf_reader import PDFTextReader


class FakePage:
    def __init__(self, text: str | None) -> None:
        self._text = text

    def extract_text(self) -> str | None:
        return self._text


class FakePdfReader:
    def __init__(self, path: str) -> None:
        self.path = path
        self.pages = [FakePage("page 1"), FakePage(None), FakePage("page 3")]


# Purpose: verify PDFTextReader joins all page text and tolerates missing page text.
def test_extract_text_joins_page_content(monkeypatch):
    monkeypatch.setattr(pdf_reader, "PdfReader", FakePdfReader)

    text = PDFTextReader().extract_text(Path("statement.pdf"))

    assert text == "page 1\n\npage 3"
