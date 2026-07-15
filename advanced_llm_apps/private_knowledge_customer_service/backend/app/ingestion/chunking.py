import re
from dataclasses import dataclass
from typing import Any

from app.ingestion.parsers.base import ParsedSection


PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
INLINE_WHITESPACE = re.compile(r"[ \t]+")


@dataclass(frozen=True, slots=True)
class CanonicalChunk:
    chunk_index: int
    text: str
    locator: dict[str, Any]


def _normalize(text: str) -> str:
    lines = [INLINE_WHITESPACE.sub(" ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _split_text(text: str, max_characters: int) -> list[str]:
    paragraphs = [
        _normalize(paragraph)
        for paragraph in PARAGRAPH_BREAK.split(text)
        if _normalize(paragraph)
    ]
    parts: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_characters:
            parts.append(paragraph)
            continue
        parts.extend(
            paragraph[start : start + max_characters]
            for start in range(0, len(paragraph), max_characters)
        )
    return parts


def chunk_sections(
    sections: list[ParsedSection], max_characters: int = 1_500
) -> list[CanonicalChunk]:
    if max_characters <= 0:
        raise ValueError("max_characters must be positive")

    chunks: list[CanonicalChunk] = []
    for section in sections:
        for text in _split_text(section.text, max_characters):
            chunks.append(
                CanonicalChunk(
                    chunk_index=len(chunks),
                    text=text,
                    locator=dict(section.locator),
                )
            )
    return chunks
