from pathlib import Path

from app.ingestion.parsers.base import DocumentParser, ParsedSection
from app.ingestion.parsers.docx import DocxParser
from app.ingestion.parsers.pdf import PdfParser
from app.ingestion.parsers.pptx import PptxParser
from app.ingestion.parsers.text import TextParser
from app.ingestion.parsers.xlsx import XlsxParser


PARSERS: dict[str, DocumentParser] = {
    ".pdf": PdfParser(),
    ".docx": DocxParser(),
    ".md": TextParser(),
    ".txt": TextParser(),
    ".xlsx": XlsxParser(),
    ".pptx": PptxParser(),
}


def parse_document(path: Path) -> list[ParsedSection]:
    try:
        parser = PARSERS[path.suffix.lower()]
    except KeyError as error:
        raise ValueError(f"unsupported document type: {path.suffix}") from error
    return parser.parse(path)

