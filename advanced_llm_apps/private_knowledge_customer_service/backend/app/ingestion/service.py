from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from types import TracebackType
from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.orm import sessionmaker

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
    total: int = 0
    processed: int = 0
    current_path: str | None = None
    limit: int | None = None
    prefix: str | None = None
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


class PreparedIndexUpdate(Protocol):
    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class KnowledgeIndex(Protocol):
    def prepare_replace(
        self,
        entry: InventoryEntry,
        chunks: list[CanonicalChunk],
    ) -> PreparedIndexUpdate: ...

    def delete_source(
        self,
        partition: KnowledgePartition,
        relative_path: str,
    ) -> None: ...


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
        self.reports[report.id] = ScanReport(
            id=report.id,
            trigger=report.trigger,
            status=report.status,
            added=report.added,
            updated=report.updated,
            deleted=report.deleted,
            failed=report.failed,
            skipped=report.skipped,
            total=report.total,
            processed=report.processed,
            current_path=report.current_path,
            limit=report.limit,
            prefix=report.prefix,
            errors=list(report.errors),
        )

    def get_report(self, run_id: UUID) -> ScanReport | None:
        return self.reports.get(run_id)


class SqlAlchemyScanRepository:
    def __init__(self, bind: Engine | Session) -> None:
        self.session = bind if isinstance(bind, Session) else None
        self.factory = (
            None
            if isinstance(bind, Session)
            else sessionmaker(bind=bind, expire_on_commit=False)
        )

    def _session_scope(self) -> "_SessionScope":
        return _SessionScope(self.session, self.factory)

    def list_sources(self, knowledge_root: Path) -> dict[str, StoredSource]:
        with self._session_scope() as session:
            statement = (
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.knowledge_root == str(knowledge_root.resolve()),
                    KnowledgeSource.index_status != IndexStatus.DELETED,
                )
                .options(selectinload(KnowledgeSource.chunks))
            )
            sources = session.scalars(statement).all()
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
                        for chunk in sorted(
                            source.chunks, key=lambda item: item.chunk_index
                        )
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
        with self._session_scope() as session:
            with session.begin_nested():
                source = session.scalar(
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
                    session.add(source)
                else:
                    source.chunks.clear()
                    session.flush()
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
                session.flush()
            session.commit()

    def delete_source(self, knowledge_root: Path, relative_path: str) -> None:
        with self._session_scope() as session:
            source = session.scalar(
                select(KnowledgeSource).where(
                    KnowledgeSource.knowledge_root == str(knowledge_root.resolve()),
                    KnowledgeSource.relative_path == relative_path,
                )
            )
            if source is not None:
                session.delete(source)
                session.commit()

    def save_report(self, report: ScanReport) -> None:
        with self._session_scope() as session:
            existing = session.get(ScanRun, report.id)
            row = existing or ScanRun(id=report.id, trigger=report.trigger)
            row.status = RunStatus(report.status)
            row.finished_at = (
                None if report.status == RunStatus.RUNNING.value else datetime.now(UTC)
            )
            row.added_count = report.added
            row.updated_count = report.updated
            row.deleted_count = report.deleted
            row.failed_count = report.failed
            row.skipped_count = report.skipped
            row.error_summary = {
                "errors": report.errors,
                "total": report.total,
                "processed": report.processed,
                "current_path": report.current_path,
                "limit": report.limit,
                "prefix": report.prefix,
            }
            if existing is None:
                session.add(row)
            session.commit()

    def get_report(self, run_id: UUID) -> ScanReport | None:
        with self._session_scope() as session:
            row = session.get(ScanRun, run_id)
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
                total=row.error_summary.get("total", 0),
                processed=row.error_summary.get("processed", 0),
                current_path=row.error_summary.get("current_path"),
                limit=row.error_summary.get("limit"),
                prefix=row.error_summary.get("prefix"),
                errors=row.error_summary.get("errors", []),
            )


class _SessionScope:
    def __init__(
        self,
        session: Session | None,
        factory: sessionmaker[Session] | None,
    ) -> None:
        self.session = session
        self.factory = factory
        self.created: Session | None = None

    def __enter__(self) -> Session:
        if self.session is not None:
            return self.session
        assert self.factory is not None
        self.created = self.factory()
        return self.created

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.created is not None:
            self.created.close()


class ScanService:
    def __init__(
        self,
        knowledge_root: Path,
        repository: ScanRepository,
        knowledge_index: KnowledgeIndex | None = None,
    ) -> None:
        self.knowledge_root = knowledge_root
        self.repository = repository
        self.knowledge_index = knowledge_index
        self._scan_lock = Lock()
        self._active_report: ScanReport | None = None

    def start_scan(
        self,
        trigger: str,
        *,
        limit: int | None = None,
        prefix: str | None = None,
    ) -> tuple[ScanReport, bool]:
        with self._scan_lock:
            if self._active_report and self._active_report.status == "running":
                return self._active_report, False
            report = ScanReport(trigger=trigger, limit=limit, prefix=prefix)
            self._active_report = report
            self.repository.save_report(report)
            return report, True

    def run_started_scan(
        self,
        report_id: UUID,
        limit: int | None = None,
        prefix: str | None = None,
    ) -> None:
        report = self.get_report(report_id)
        if report is None:
            return
        try:
            completed = self.scan(
                report.trigger,
                report_id=report.id,
                limit=limit,
                prefix=prefix,
            )
        except Exception as error:
            completed = ScanReport(
                id=report.id,
                trigger=report.trigger,
                status="failed",
                total=report.total,
                processed=report.processed,
                current_path=report.current_path,
                limit=report.limit,
                prefix=report.prefix,
                errors=[{"path": "<scan>", "error": f"{type(error).__name__}: {error}"}],
            )
            self.repository.save_report(completed)
        with self._scan_lock:
            if self._active_report and self._active_report.id == completed.id:
                self._active_report = completed

    def scan(
        self,
        trigger: str,
        *,
        report_id: UUID | None = None,
        limit: int | None = None,
        prefix: str | None = None,
    ) -> ScanReport:
        report = ScanReport(
            id=report_id or uuid4(),
            trigger=trigger,
            limit=limit,
            prefix=prefix,
        )
        entries = inventory_knowledge_root(self.knowledge_root)
        full_scan = limit is None and prefix is None
        if prefix is not None:
            normalized_prefix = prefix.strip("/")
            entries = [
                entry
                for entry in entries
                if entry.relative_path.as_posix().startswith(normalized_prefix)
            ]
        if limit is not None:
            entries = entries[:limit]
        report.total = len(entries)
        if prefix is not None and not entries:
            report.failed = 1
            report.status = "failed"
            report.errors.append(
                {
                    "path": normalized_prefix,
                    "error": "no files matched scan prefix",
                }
            )
            self.repository.save_report(report)
            return report
        self.repository.save_report(report)
        stored_sources = self.repository.list_sources(self.knowledge_root)
        current_paths = {entry.relative_path.as_posix() for entry in entries}

        for entry in entries:
            relative_path = entry.relative_path.as_posix()
            report.current_path = relative_path
            self.repository.save_report(report)
            previous = stored_sources.get(relative_path)
            if previous and previous.content_hash == entry.fingerprint.content_hash:
                report.skipped += 1
                report.processed += 1
                self.repository.save_report(report)
                continue

            try:
                chunks = chunk_sections(parse_document(entry.absolute_path))
                if not chunks:
                    raise ValueError("document contains no indexable text")
                prepared = (
                    self.knowledge_index.prepare_replace(entry, chunks)
                    if self.knowledge_index
                    else None
                )
                try:
                    self.repository.atomic_replace(
                        self.knowledge_root,
                        entry,
                        chunks,
                    )
                except Exception:
                    if prepared:
                        prepared.rollback()
                    raise
                if prepared:
                    prepared.commit()
            except Exception as error:
                report.failed += 1
                report.errors.append(
                    {
                        "path": relative_path,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
                report.processed += 1
                self.repository.save_report(report)
                continue

            if previous is None:
                report.added += 1
            else:
                report.updated += 1
            report.processed += 1
            self.repository.save_report(report)

        for relative_path in sorted(set(stored_sources) - current_paths) if full_scan else []:
            try:
                report.current_path = relative_path
                self.repository.save_report(report)
                if self.knowledge_index:
                    self.knowledge_index.delete_source(
                        stored_sources[relative_path].partition,
                        relative_path,
                    )
                self.repository.delete_source(self.knowledge_root, relative_path)
                report.deleted += 1
                report.processed += 1
                self.repository.save_report(report)
            except Exception as error:
                report.failed += 1
                report.errors.append(
                    {
                        "path": relative_path,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
                report.processed += 1
                self.repository.save_report(report)

        report.status = "partial" if report.failed else "succeeded"
        if report.failed and not any(
            (report.added, report.updated, report.deleted, report.skipped)
        ):
            report.status = "failed"
        report.current_path = None
        self.repository.save_report(report)
        return report

    def get_report(self, run_id: UUID) -> ScanReport | None:
        return self.repository.get_report(run_id)
