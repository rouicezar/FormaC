from dataclasses import dataclass
from typing import Any

from app.domain.models import KnowledgePartition


@dataclass(frozen=True, slots=True)
class EvidenceMatch:
    """The multimodal RAG citation contract plus local source location."""

    citation: str
    source: str
    similarity: float
    evidence: str
    partition: KnowledgePartition
    locator: dict[str, Any]

    def as_payload(self) -> dict[str, Any]:
        return {
            "citation": self.citation,
            "source": self.source,
            "modality": "document",
            "similarity": self.similarity,
            "evidence": self.evidence,
            "partition": self.partition.value,
            "locator": self.locator,
        }


@dataclass(frozen=True, slots=True)
class EvidencePacket:
    provider: str
    matches: tuple[EvidenceMatch, ...]

    def as_payload(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "matches": [match.as_payload() for match in self.matches],
        }
