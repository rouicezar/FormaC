from pathlib import Path

from app.ingestion.parsers.base import ParsedSection


class TextParser:
    def parse(self, path: Path) -> list[ParsedSection]:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        return [
            ParsedSection(
                text=text,
                locator={"line_start": 1, "line_end": len(text.splitlines())},
            )
        ]

