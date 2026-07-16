from sqlalchemy import UniqueConstraint

from app.domain.models import Base, DocumentChunk, KnowledgeSource


EXPECTED_TABLES = {
    "knowledge_sources",
    "document_chunks",
    "feishu_events",
    "interaction_records",
    "scan_runs",
    "identity_whitelist",
    "conversations",
    "messages",
    "handoff_tickets",
    "model_configs",
    "audit_events",
}


def test_metadata_contains_all_core_tables() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_source_path_is_unique_within_a_knowledge_root() -> None:
    constraints = {
        tuple(constraint.columns.keys())
        for constraint in KnowledgeSource.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert ("knowledge_root", "relative_path") in constraints


def test_document_chunks_use_pgvector_and_traceable_locations() -> None:
    columns = DocumentChunk.__table__.columns

    assert str(columns["embedding"].type) == "VECTOR(1024)"
    assert columns["source_locator"].nullable is False
    assert columns["partition"].nullable is False


def test_sensitive_and_lifecycle_columns_are_non_nullable() -> None:
    tables = Base.metadata.tables

    assert tables["knowledge_sources"].c.partition.nullable is False
    assert tables["knowledge_sources"].c.index_status.nullable is False
    assert tables["scan_runs"].c.status.nullable is False
    assert tables["conversations"].c.state.nullable is False
    assert tables["handoff_tickets"].c.status.nullable is False
    assert tables["model_configs"].c.allow_sensitive_to_cloud.nullable is False


def test_file_metadata_uses_bigint_for_filesystem_values() -> None:
    columns = KnowledgeSource.__table__.columns

    assert str(columns["modified_at_ns"].type) == "BIGINT"
    assert str(columns["size_bytes"].type) == "BIGINT"
