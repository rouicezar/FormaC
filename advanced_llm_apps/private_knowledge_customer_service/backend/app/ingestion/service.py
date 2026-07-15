from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models import (
    DocumentChunk,
    IndexStatus,
    KnowledgePartition,
    KnowledgeSource,
    RunStatus,
    ScanRun,
)
from app.ingestion.chunking import CanonicalChunk, chunk_sections
from app.ingestion.inventory import InventoryEntry, inventory_knowledge_root
from app.ingestion.parsers.registry import parse_document


PARSER_VERSION = "1"


@dataclass(frozen=True, slots=True)
class StoredSource:
    relative_path: str
    partition: KnowledgePartition
    content_hash: str
    modified_at_ns: int
    size_bytes: int
    chunks: tuple[CanonicalChunk, ...]


@dataclass(slots=True)
class ScanReport:
    id: UUID = field(default_factory=uuid4)
    trigger: str = "manual"
    status: str = "running"
    added: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    skipped: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        return {
            "added": self.added,
            "updated": self.updated,
            "deleted": self.deleted,
            "failed": self.failed,
            "skipped": self.skipped,
        }


class ScanRepository(Protocol):
    def list_sources(self, knowledge_root: Path) -> dict[str, StoredSource]: ...

    def atomic_replace(
        self,
        knowledge_root: Path,
        entry: InventoryEntry,
        chunks: list[CanonicalChunk],
    ) -> None: ...

    def delete_source(self, knowledge_root: Path, relative_path: str) -> None: ...

    def save_report(self, report: ScanReport) -> None: ...

    def get_report(self, run_id: UUID) -> ScanReport | None: ...


class InMemoryScanRepository:
    def __init__(self) -> None:
        self.sources: dict[str, StoredSource] = {}
        self.reports: dict[UUID, ScanReport] = {}
        self.fail_replacements: set[str] = set()
        self.deleted_paths: list[str] = []

    def list_sources(self, knowledge_root: Path) -> dict[str, StoredSource]:
        return dict(self.sources)

    def atomic_replace(
        self,
        knowledge_root: Path,
        entry: InventoryEntry,
        chunks: list[CanonicalChunk],
    ) -> None:
        key = entry.relative_path.as_posix()
        if key in self.fail_replacements:
            raise RuntimeError("simulated transactional replacement failure")
        replacement = StoredSource(
            relative_path=key,
            partition=entry.partition,
            content_hash=entry.fingerprint.content_hash,
            modified_at_ns=entry.fingerprint.modified_at_ns,
            size_bytes=entry.fingerprint.size_bytes,
            chunks=tuple(chunks),
        )
        self.sources[key] = replacement

    def delete_source(self, knowledge_root: Path, relative_path: str) -> None:
        self.sources.pop(relative_path, None)
        self.deleted_paths.append(relative_path)

    def save_report(self, report: ScanReport) -> None:
        self.reports[report.id] = report

    def get_report(self, run_id: UUID) -> ScanReport | None:
        return self.reports.get(run_id)


class SqlAlchemyScanRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_sources(self, knowledge_root: Path) -> dict[str, StoredSource]:
        statement = (
            select(KnowledgeSource)
            .where(
                KnowledgeSource.knowledge_root == str(knowledge_root.resolve()),
                KnowledgeSource.index_status != IndexStatus.DELETED,
            )
            .options(selectinload(KnowledgeSource.chunks))
        )
        sources = self.session.scalars(statement).all()
        return {
            source.relative_path: StoredSource(
                relative_path=source.relative_path,
                partition=source.partition,
                content_hash=source.content_hash,
                modified_at_ns=source.modified_at_ns,
                size_bytes=source.size_bytes,
                chunks=tuple(
                    CanonicalChunk(
                        chunk_index=chunk.chunk_index,
                        text=chunk.content,
                        locator=chunk.source_locator,
                    )
                    for chunk in sorted(source.chunks, key=lambda item: item.chunk_index)
                ),
            )
            for source in sources
        }

    def atomic_replace(
        self,
        knowledge_root: Path,
        entry: InventoryEntry,
        chunks: list[CanonicalChunk],
    ) -> None:
        root_value = str(knowledge_root.resolve())
        relative_path = entry.relative_path.as_posix()
        with self.session.begin_nested():
            source = self.session.scalar(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.knowledge_root == root_value,
                    KnowledgeSource.relative_path == relative_path,
                )
                .options(selectinload(KnowledgeSource.chunks))
            )
            if source is None:
                source = KnowledgeSource(
                    knowledge_root=root_value,
                    relative_path=relative_path,
                    partition=entry.partition,
                    content_hash=entry.fingerprint.content_hash,
                    modified_at_ns=entry.fingerprint.modified_at_ns,
                    size_bytes=entry.fingerprint.size_bytes,
                    parser_version=PARSER_VERSION,
                    index_status=IndexStatus.READY,
                )
                self.session.add(source)
            else:
                source.chunks.clear()
                self.session.flush()
                source.partition = entry.partition
                source.content_hash = entry.fingerprint.content_hash
                source.modified_at_ns = entry.fingerprint.modified_at_ns
                source.size_bytes = entry.fingerprint.size_bytes
                source.parser_version = PARSER_VERSION
                source.index_status = IndexStatus.READY
                source.last_error = None

            source.chunks.extend(
                DocumentChunk(
                    chunk_index=chunk.chunk_index,
                    partition=entry.partition,
                    content=chunk.text,
                    source_locator=chunk.locator,
                )
                for chunk in chunks
            )
            self.session.flush()
        self.session.commit()

    def delete_source(self, knowledge_root: Path, relative_path: str) -> None:
        source = self.session.scalar(
            select(KnowledgeSource).where(
                KnowledgeSource.knowledge_root == str(knowledge_root.resolve()),
                KnowledgeSource.relative_path == relative_path,
            )
        )
        if source is not None:
            self.session.delete(source)
            self.session.commit()

    def save_report(self, report: ScanReport) -> None:
        existing = self.session.get(ScanRun, report.id)
        row = existing or ScanRun(id=report.id, trigger=report.trigger)
        row.status = RunStatus(report.status)
        row.finished_at = datetime.now(UTC)
        row.added_count = report.added
        row.updated_count = report.updated
        row.deleted_count = report.deleted
        row.failed_count = report.failed
        row.skipped_count = report.skipped
        row.error_summary = {"errors": report.errors}
        if existing is None:
            self.session.add(row)
        self.session.commit()

    def get_report(self, run_id: UUID) -> ScanReport | None:
        row = self.session.get(ScanRun, run_id)
        if row is None:
            return None
        return ScanReport(
            id=row.id,
            trigger=row.trigger,
            status=row.status.value,
            added=row.added_count,
            updated=row.updated_count,
            deleted=row.deleted_count,
            failed=row.failed_count,
            skipped=row.skipped_count,
            errors=row.error_summary.get("errors", []),
        )


class ScanService:
    def __init__(self, knowledge_root: Path, repository: ScanRepository) -> None:
        self.knowledge_root = knowledge_root
        self.repository = repository

    def scan(self, trigger: str) -> ScanReport:
        report = ScanReport(trigger=trigger)
        entries = inventory_knowledge_root(self.knowledge_root)
        stored_sources = self.repository.list_sources(self.knowledge_root)
        current_paths = {entry.relative_path.as_posix() for entry in entries}

        for entry in entries:
            relative_path = entry.relative_path.as_posix()
            previous = stored_sources.get(relative_path)
            if previous and previous.content_hash == entry.fingerprint.content_hash:
                report.skipped += 1
                continue

            try:
                chunks = chunk_sections(parse_document(entry.absolute_path))
                if not chunks:
                    raise ValueError("document contains no indexable text")
                self.repository.atomic_replace(
                    self.knowledge_root,
                    entry,
                    chunks,
                )
            except Exception as error:
                report.failed += 1
                report.errors.append(
                    {
                        "path": relative_path,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
                continue

            if previous is None:
                report.added += 1
            else:
                report.updated += 1

        for relative_path in sorted(set(stored_sources) - current_paths):
            try:
                self.repository.delete_source(self.knowledge_root, relative_path)
                report.deleted += 1
            except Exception as error:
                report.failed += 1
                report.errors.append(
                    {
                        "path": relative_path,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )

        report.status = "partial" if report.failed else "succeeded"
        if report.failed and not any(
            (report.added, report.updated, report.deleted, report.skipped)
        ):
            report.status = "failed"
        self.repository.save_report(report)
        return report

    def get_report(self, run_id: UUID) -> ScanReport | None:
        return self.repository.get_report(run_id)
