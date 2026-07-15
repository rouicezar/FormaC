from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class ModelLocation(StrEnum):
    CLOUD = "cloud"
    LOCAL = "local"


@dataclass(frozen=True, slots=True)
class ModelRequest:
    system: str
    user: str


class ModelProvider(Protocol):
    name: str
    location: ModelLocation

    def generate(self, request: ModelRequest) -> str: ...
