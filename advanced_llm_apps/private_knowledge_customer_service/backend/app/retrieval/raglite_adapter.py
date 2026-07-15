"""Thin adapter around the repository's existing RAGLite retrieval template.

Reuse sources:
- ``rag_tutorials/local_hybrid_search_rag/local_main.py`` for the exact
  ``hybrid_search -> retrieve_chunks -> rerank_chunks`` call chain.
- ``rag_tutorials/multimodal_agentic_rag/backend/rag_store.py`` for the
  ``citation/source/similarity/evidence`` response contract.

This module intentionally does not implement vector search, keyword search,
fusion, or reranking. Public and sensitive content use distinct RAGLite stores
so an external identity cannot accidentally query sensitive rows.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from app.domain.models import KnowledgePartition
from app.retrieval.evidence import EvidenceMatch, EvidencePacket


class IdentityKind(StrEnum):
    EXTERNAL = "external"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class RetrievalStore:
    partition: KnowledgePartition
    config: Any


class RagLiteChunk(Protocol):
    id: str
    body: str
    metadata_: dict[str, Any]


class RagLiteApi(Protocol):
    def has_chunks(self, *, config: Any) -> bool: ...

    def hybrid_search(
        self, query: str, *, num_results: int, config: Any
    ) -> tuple[list[str], list[float]]: ...

    def retrieve_chunks(self, chunk_ids: list[str], *, config: Any) -> list[RagLiteChunk]: ...

    def rerank_chunks(
        self, query: str, chunks: list[RagLiteChunk], *, config: Any
    ) -> list[RagLiteChunk]: ...


class ImportedRagLiteApi:
    """Lazy imports keep health and scan commands usable before RAGLite setup."""

    @staticmethod
    def has_chunks(*, config: Any) -> bool:
        from raglite._database import Chunk, create_database_engine
        from sqlmodel import Session, select

        with Session(create_database_engine(config)) as session:
            return session.exec(select(Chunk.id).limit(1)).first() is not None

    @staticmethod
    def hybrid_search(query: str, *, num_results: int, config: Any):
        from raglite import hybrid_search

        return hybrid_search(query, num_results=num_results, config=config)

    @staticmethod
    def retrieve_chunks(chunk_ids: list[str], *, config: Any):
        from raglite import retrieve_chunks

        return retrieve_chunks(chunk_ids, config=config)

    @staticmethod
    def rerank_chunks(query: str, chunks: list[RagLiteChunk], *, config: Any):
        from raglite import rerank_chunks

        return rerank_chunks(query, chunks, config=config)


class RagLiteHybridRetriever:
    def __init__(
        self,
        *,
        public_store: RetrievalStore,
        sensitive_store: RetrievalStore,
        raglite: RagLiteApi | None = None,
    ) -> None:
        if public_store.partition is not KnowledgePartition.PUBLIC:
            raise ValueError("public_store must use the public partition")
        if sensitive_store.partition is not KnowledgePartition.SENSITIVE:
            raise ValueError("sensitive_store must use the sensitive partition")
        self.public_store = public_store
        self.sensitive_store = sensitive_store
        self.raglite = raglite or ImportedRagLiteApi()

    def search(
        self,
        query: str,
        *,
        identity: IdentityKind,
        num_results: int = 5,
    ) -> EvidencePacket:
        stores = [self.public_store]
        if identity is IdentityKind.INTERNAL:
            stores.append(self.sensitive_store)

        candidates: list[tuple[RagLiteChunk, float, KnowledgePartition]] = []
        for store in stores:
            # RAGLite 0.2.1's PostgreSQL vector_search raises while unpacking
            # an empty result set. Skip an empty physical store before calling
            # the unchanged template search chain.
            if not self.raglite.has_chunks(config=store.config):
                continue
            chunk_ids, scores = self.raglite.hybrid_search(
                query,
                num_results=num_results,
                config=store.config,
            )
            if not chunk_ids:
                continue
            score_by_id = dict(zip(chunk_ids, scores, strict=True))
            chunks = self.raglite.retrieve_chunks(chunk_ids, config=store.config)
            candidates.extend(
                (chunk, score_by_id[chunk.id], store.partition)
                for chunk in chunks
            )

        if not candidates:
            return EvidencePacket(provider="raglite-hybrid", matches=())

        # Each physical store computes its own RRF scores, so those scores are not
        # sufficient for cross-store ordering. Reuse RAGLite's existing reranker
        # once over the combined candidates instead of implementing a new ranker.
        reranked = self.raglite.rerank_chunks(
            query,
            [candidate[0] for candidate in candidates],
            config=self.public_store.config,
        )
        candidate_by_id = {
            chunk.id: (score, partition)
            for chunk, score, partition in candidates
        }
        matches = [
            self._to_evidence(
                chunk,
                candidate_by_id[chunk.id][0],
                candidate_by_id[chunk.id][1],
            )
            for chunk in reranked
        ]
        return EvidencePacket(provider="raglite-hybrid", matches=tuple(matches[:num_results]))

    @staticmethod
    def _to_evidence(
        chunk: RagLiteChunk,
        score: float,
        partition: KnowledgePartition,
    ) -> EvidenceMatch:
        source = chunk.metadata_.get("source")
        if not isinstance(source, str) or not source:
            raise ValueError(f"RAGLite chunk {chunk.id} is missing source metadata")
        locator = chunk.metadata_.get("locator", {})
        if not isinstance(locator, dict):
            raise ValueError(f"RAGLite chunk {chunk.id} has invalid locator metadata")
        return EvidenceMatch(
            citation=chunk.id,
            source=source,
            similarity=float(score),
            evidence=chunk.body.strip(),
            partition=partition,
            locator=locator,
        )
