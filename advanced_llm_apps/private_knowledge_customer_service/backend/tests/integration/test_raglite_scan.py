import os
from pathlib import Path

import pytest
from raglite import RAGLiteConfig
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.domain.models import KnowledgePartition
from app.indexing.raglite_writer import (
    ImportedRagLiteIndexBackend,
    RagLiteIndexWriter,
    RagLiteStore,
)
from app.ingestion.service import ScanService, SqlAlchemyScanRepository
from app.retrieval.raglite_adapter import (
    IdentityKind,
    RagLiteHybridRetriever,
    RetrievalStore,
)


DATABASE_URL = os.getenv("PKCS_TEST_DATABASE_URL")
PUBLIC_RAG_URL = os.getenv("PKCS_TEST_PUBLIC_RAG_URL")
SENSITIVE_RAG_URL = os.getenv("PKCS_TEST_SENSITIVE_RAG_URL")
pytestmark = pytest.mark.skipif(
    not all((DATABASE_URL, PUBLIC_RAG_URL, SENSITIVE_RAG_URL)),
    reason="all three PostgreSQL integration URLs are required",
)


def make_config(url: str) -> RAGLiteConfig:
    return RAGLiteConfig(
        db_url=url,
        embedder="ollama/embeddinggemma:latest",
    )


def clear_raglite(config: RAGLiteConfig) -> None:
    from raglite._database import Document, create_database_engine
    from sqlmodel import Session as RagSession, select

    backend = ImportedRagLiteIndexBackend()
    with RagSession(create_database_engine(config)) as session:
        document_ids = list(session.scalars(select(Document.id)))
    backend.delete_documents(config, document_ids)


def test_real_scan_updates_partitioned_raglite_indexes(tmp_path: Path) -> None:
    assert DATABASE_URL and PUBLIC_RAG_URL and SENSITIVE_RAG_URL
    public_config = make_config(PUBLIC_RAG_URL)
    sensitive_config = make_config(SENSITIVE_RAG_URL)
    clear_raglite(public_config)
    clear_raglite(sensitive_config)

    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE document_chunks, knowledge_sources, scan_runs "
                "RESTART IDENTITY CASCADE"
            )
        )

    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    public_file = root / "public" / "退款说明.txt"
    sensitive_file = root / "sensitive" / "折扣规则.txt"
    public_file.write_text("公开退款期限为七个自然日。", encoding="utf-8")
    sensitive_file.write_text("内部折扣底线为八五折。", encoding="utf-8")

    writer = RagLiteIndexWriter(
        public_store=RagLiteStore(KnowledgePartition.PUBLIC, public_config),
        sensitive_store=RagLiteStore(KnowledgePartition.SENSITIVE, sensitive_config),
    )
    retriever = RagLiteHybridRetriever(
        public_store=RetrievalStore(KnowledgePartition.PUBLIC, public_config),
        sensitive_store=RetrievalStore(KnowledgePartition.SENSITIVE, sensitive_config),
    )

    with Session(engine) as session:
        service = ScanService(root, SqlAlchemyScanRepository(session), writer)
        initial = service.scan("manual")
        assert initial.counts()["added"] == 2

        external = retriever.search("内部折扣底线", identity=IdentityKind.EXTERNAL)
        internal = retriever.search("内部折扣底线", identity=IdentityKind.INTERNAL)
        assert all(match.partition is KnowledgePartition.PUBLIC for match in external.matches)
        assert internal.matches[0].source == "sensitive/折扣规则.txt"
        assert internal.matches[0].locator == {"line_start": 1, "line_end": 1}

        public_file.write_text("公开退款期限调整为十四个自然日。", encoding="utf-8")
        updated = service.scan("manual")
        assert updated.updated == 1
        refreshed = retriever.search("退款期限调整", identity=IdentityKind.EXTERNAL)
        assert any("十四个自然日" in match.evidence for match in refreshed.matches)
        assert all("七个自然日" not in match.evidence for match in refreshed.matches)

        sensitive_file.unlink()
        deleted = service.scan("manual")
        assert deleted.deleted == 1
        after_delete = retriever.search("内部折扣底线", identity=IdentityKind.INTERNAL)
        assert all(match.partition is KnowledgePartition.PUBLIC for match in after_delete.matches)

    engine.dispose()
