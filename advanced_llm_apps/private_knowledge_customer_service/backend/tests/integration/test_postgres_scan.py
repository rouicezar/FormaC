import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.ingestion.service import ScanService, SqlAlchemyScanRepository


DATABASE_URL = os.getenv("PKCS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="PKCS_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
def database_engine():
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE document_chunks, knowledge_sources, scan_runs "
                "RESTART IDENTITY CASCADE"
            )
        )
    try:
        yield engine
    finally:
        engine.dispose()


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    return root


def test_real_pgvector_migration_and_scan_persist_across_sessions(
    tmp_path: Path, database_engine
) -> None:
    root = make_root(tmp_path)
    document = root / "public" / "faq.txt"
    document.write_text("First persisted answer", encoding="utf-8")

    with Session(database_engine) as first_session:
        first_report = ScanService(
            root, SqlAlchemyScanRepository(first_session)
        ).scan(trigger="manual")
        run_id = first_report.id
        assert first_report.added == 1

    with Session(database_engine) as restarted_session:
        restarted_repository = SqlAlchemyScanRepository(restarted_session)
        persisted = restarted_repository.list_sources(root)
        persisted_report = restarted_repository.get_report(run_id)
        assert persisted["public/faq.txt"].chunks[0].text == "First persisted answer"
        assert persisted_report is not None
        assert persisted_report.status == "succeeded"

        document.write_text("Updated persisted answer", encoding="utf-8")
        updated_report = ScanService(root, restarted_repository).scan(trigger="manual")
        assert updated_report.updated == 1

    with Session(database_engine) as final_session:
        final_repository = SqlAlchemyScanRepository(final_session)
        assert (
            final_repository.list_sources(root)["public/faq.txt"].chunks[0].text
            == "Updated persisted answer"
        )
        document.unlink()
        deleted_report = ScanService(root, final_repository).scan(trigger="manual")
        assert deleted_report.deleted == 1
        assert final_repository.list_sources(root) == {}


def test_vector_extension_and_expected_tables_exist(database_engine) -> None:
    with database_engine.connect() as connection:
        extension = connection.scalar(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        tables = set(
            connection.scalars(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
                )
            )
        )

    assert extension == "vector"
    assert tables == {
        "audit_events",
        "conversations",
        "document_chunks",
        "feishu_events",
        "handoff_tickets",
        "identity_whitelist",
        "knowledge_sources",
        "messages",
        "model_configs",
        "scan_runs",
    }
