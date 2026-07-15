from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class ParsedSection:
    text: str
    locator: dict[str, Any]


class DocumentParser(Protocol):
    def parse(self, path: Path) -> list[ParsedSection]: ...

