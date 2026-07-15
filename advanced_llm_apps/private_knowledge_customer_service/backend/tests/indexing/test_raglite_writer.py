from dataclasses import dataclass
from pathlib import Path

import pytest

from app.domain.models import KnowledgePartition
from app.indexing.raglite_writer import RagLiteIndexWriter, RagLiteStore
from app.ingestion.chunking import CanonicalChunk
from app.ingestion.fingerprint import FileFingerprint
from app.ingestion.inventory import InventoryEntry


@dataclass
class FakeBackend:
    documents: dict[tuple[str, str], list[str]]
    inserted: list[tuple[str, str, CanonicalChunk]]
    deleted: list[tuple[str, tuple[str, ...]]]
    fail_at_chunk: int | None = None

    def source_document_ids(self, config: object, relative_path: str) -> list[str]:
        return list(self.documents.get((str(config), relative_path), []))

    def insert_chunk(self, config: object, relative_path: str, partition, chunk):
        if self.fail_at_chunk == chunk.chunk_index:
            raise RuntimeError("simulated RAGLite insertion failure")
        document_id = f"new-{partition.value}-{chunk.chunk_index}"
        self.inserted.append((str(config), relative_path, chunk))
        return document_id

    def delete_documents(self, config: object, document_ids: list[str]) -> None:
        self.deleted.append((str(config), tuple(document_ids)))


def entry(partition: KnowledgePartition) -> InventoryEntry:
    return InventoryEntry(
        absolute_path=Path("/knowledge") / partition.value / "policy.md",
        relative_path=Path(partition.value) / "policy.md",
        partition=partition,
        fingerprint=FileFingerprint(
            modified_at_ns=1,
            size_bytes=10,
            content_hash="a" * 64,
        ),
    )


def chunks() -> list[CanonicalChunk]:
    return [
        CanonicalChunk(0, "第一页规则", {"page": 1}),
        CanonicalChunk(1, "第二页规则", {"page": 2}),
    ]


def writer(backend: FakeBackend) -> RagLiteIndexWriter:
    return RagLiteIndexWriter(
        public_store=RagLiteStore(KnowledgePartition.PUBLIC, "public-db"),
        sensitive_store=RagLiteStore(KnowledgePartition.SENSITIVE, "sensitive-db"),
        backend=backend,
    )


def test_prepare_uses_partition_store_and_commit_removes_old_documents():
    backend = FakeBackend(
        documents={("sensitive-db", "sensitive/policy.md"): ["old-1"]},
        inserted=[],
        deleted=[],
    )

    prepared = writer(backend).prepare_replace(entry(KnowledgePartition.SENSITIVE), chunks())
    prepared.commit()

    assert {item[0] for item in backend.inserted} == {"sensitive-db"}
    assert backend.deleted == [("sensitive-db", ("old-1",))]


def test_rollback_removes_new_documents_and_preserves_old_documents():
    backend = FakeBackend(
        documents={("public-db", "public/policy.md"): ["old-1"]},
        inserted=[],
        deleted=[],
    )

    prepared = writer(backend).prepare_replace(entry(KnowledgePartition.PUBLIC), chunks())
    prepared.rollback()

    assert backend.deleted == [
        ("public-db", ("new-public-0", "new-public-1")),
    ]


def test_partial_insert_failure_cleans_up_new_documents():
    backend = FakeBackend(documents={}, inserted=[], deleted=[], fail_at_chunk=1)

    with pytest.raises(RuntimeError, match="insertion failure"):
        writer(backend).prepare_replace(entry(KnowledgePartition.PUBLIC), chunks())

    assert backend.deleted == [("public-db", ("new-public-0",))]


def test_delete_source_uses_only_its_partition_store():
    backend = FakeBackend(
        documents={("sensitive-db", "sensitive/policy.md"): ["secret-1"]},
        inserted=[],
        deleted=[],
    )

    writer(backend).delete_source(KnowledgePartition.SENSITIVE, "sensitive/policy.md")

    assert backend.deleted == [("sensitive-db", ("secret-1",))]
