from dataclasses import dataclass
from typing import Protocol

from app.retrieval.evidence import EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


class Retriever(Protocol):
    def search(
        self,
        query: str,
        *,
        identity: IdentityKind,
        num_results: int = 5,
    ) -> EvidencePacket: ...


@dataclass(frozen=True, slots=True)
class OriginalSearchService:
    """Retrieve original evidence without invoking any model provider."""

    retriever: Retriever

    def search(
        self,
        query: str,
        *,
        identity: IdentityKind,
        num_results: int = 10,
    ) -> EvidencePacket:
        return self.retriever.search(
            query,
            identity=identity,
            num_results=num_results,
        )
