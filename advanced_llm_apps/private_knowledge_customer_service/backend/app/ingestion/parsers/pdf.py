from pathlib import Path

from pypdf import PdfReader

from app.ingestion.parsers.base import ParsedSection


class PdfParser:
    def parse(self, path: Path) -> list[ParsedSection]:
        reader = PdfReader(path)
        return [
            ParsedSection(text=text, locator={"page": page_number})
            for page_number, page in enumerate(reader.pages, start=1)
            if (text := (page.extract_text() or "").strip())
        ]

