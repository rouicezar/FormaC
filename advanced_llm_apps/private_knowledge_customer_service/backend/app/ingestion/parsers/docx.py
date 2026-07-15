from pathlib import Path

from docx import Document

from app.ingestion.parsers.base import ParsedSection


class DocxParser:
    def parse(self, path: Path) -> list[ParsedSection]:
        document = Document(path)
        return [
            ParsedSection(text=text, locator={"paragraph": paragraph_number})
            for paragraph_number, paragraph in enumerate(document.paragraphs, start=1)
            if (text := paragraph.text.strip())
        ]

