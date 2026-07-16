from pathlib import Path
from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.ingestion.service import InMemoryScanRepository, ScanService
from app.main import create_app


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    return root


@dataclass
class FakePreparedUpdate:
    source: str
    committed: bool = False
    rolled_back: bool = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


class FakeKnowledgeIndex:
    def __init__(self) -> None:
        self.prepared: list[FakePreparedUpdate] = []
        self.deleted: list[tuple[str, str]] = []

    def prepare_replace(self, entry, chunks):
        update = FakePreparedUpdate(entry.relative_path.as_posix())
        self.prepared.append(update)
        return update

    def delete_source(self, partition, relative_path: str) -> None:
        self.deleted.append((partition.value, relative_path))


class ProgressProbeRepository(InMemoryScanRepository):
    def __init__(self) -> None:
        super().__init__()
        self.snapshots: list[dict[str, int | str]] = []

    def save_report(self, report) -> None:
        super().save_report(report)
        self.snapshots.append(
            {
                "status": report.status,
                "total": report.total,
                "processed": report.processed,
                "current_path": report.current_path,
                "limit": report.limit,
                "prefix": report.prefix,
                **report.counts(),
            }
        )


def test_initial_scan_and_unchanged_scan(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("Shipping takes two days", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)

    initial = service.scan(trigger="manual")
    unchanged = service.scan(trigger="manual")

    assert initial.counts() == {
        "added": 1,
        "updated": 0,
        "deleted": 0,
        "failed": 0,
        "skipped": 0,
    }
    assert unchanged.counts() == {
        "added": 0,
        "updated": 0,
        "deleted": 0,
        "failed": 0,
        "skipped": 1,
    }
    assert repository.sources["public/faq.txt"].chunks[0].text == "Shipping takes two days"


def test_scan_persists_running_progress(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "first.txt").write_text("First answer", encoding="utf-8")
    (root / "public" / "second.txt").write_text("Second answer", encoding="utf-8")
    repository = ProgressProbeRepository()
    service = ScanService(root, repository)

    report = service.scan(trigger="manual")

    assert report.added == 2
    assert {
        "status": "running",
        "total": 2,
        "processed": 1,
        "current_path": "public/first.txt",
        "limit": None,
        "prefix": None,
        "added": 1,
        "updated": 0,
        "deleted": 0,
        "failed": 0,
        "skipped": 0,
    } in repository.snapshots
    assert repository.snapshots[-1] == {
        "status": "succeeded",
        "total": 2,
        "processed": 2,
        "current_path": None,
        "limit": None,
        "prefix": None,
        "added": 2,
        "updated": 0,
        "deleted": 0,
        "failed": 0,
        "skipped": 0,
    }


def test_limited_scan_indexes_subset_and_does_not_delete_unscanned_sources(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "a.txt").write_text("A answer", encoding="utf-8")
    (root / "public" / "b.txt").write_text("B answer", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)
    service.scan(trigger="manual")

    (root / "public" / "a.txt").write_text("A replacement", encoding="utf-8")
    (root / "public" / "b.txt").unlink()
    limited = service.scan(trigger="manual", limit=1)

    assert limited.limit == 1
    assert limited.total == 1
    assert limited.processed == 1
    assert limited.updated == 1
    assert limited.deleted == 0
    assert "public/b.txt" in repository.sources


def test_prefixed_scan_indexes_matching_files_without_delete_reconciliation(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("FAQ answer", encoding="utf-8")
    (root / "public" / "other.txt").write_text("Other answer", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)
    service.scan(trigger="manual")

    (root / "public" / "faq.txt").write_text("FAQ replacement", encoding="utf-8")
    (root / "public" / "other.txt").unlink()
    prefixed = service.scan(trigger="manual", prefix="public/faq.txt")

    assert prefixed.prefix == "public/faq.txt"
    assert prefixed.total == 1
    assert prefixed.processed == 1
    assert prefixed.updated == 1
    assert prefixed.deleted == 0
    assert "public/other.txt" in repository.sources


def test_prefixed_scan_fails_when_no_files_match(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("FAQ answer", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)

    prefixed = service.scan(trigger="manual", prefix="public/missing.txt")

    assert prefixed.prefix == "public/missing.txt"
    assert prefixed.status == "failed"
    assert prefixed.total == 0
    assert prefixed.processed == 0
    assert prefixed.failed == 1
    assert prefixed.errors == [
        {
            "path": "public/missing.txt",
            "error": "no files matched scan prefix",
        }
    ]


def test_changed_and_deleted_files_update_inventory(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    path = root / "public" / "faq.txt"
    path.write_text("Version one", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)
    service.scan(trigger="manual")

    path.write_text("Version two", encoding="utf-8")
    updated = service.scan(trigger="manual")
    path.unlink()
    deleted = service.scan(trigger="manual")

    assert updated.updated == 1
    assert repository.deleted_paths == ["public/faq.txt"]
    assert deleted.deleted == 1
    assert "public/faq.txt" not in repository.sources


def test_one_bad_file_does_not_abort_the_scan(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "good.txt").write_text("Usable answer", encoding="utf-8")
    (root / "public" / "broken.pdf").write_bytes(b"not a pdf")
    repository = InMemoryScanRepository()

    report = ScanService(root, repository).scan(trigger="manual")

    assert report.added == 1
    assert report.failed == 1
    assert report.status == "partial"
    assert report.errors[0]["path"] == "public/broken.pdf"
    assert "public/good.txt" in repository.sources


def test_failed_replacement_preserves_previous_index(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    path = root / "sensitive" / "policy.md"
    path.write_text("Original policy", encoding="utf-8")
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)
    service.scan(trigger="manual")
    original_hash = repository.sources["sensitive/policy.md"].content_hash

    path.write_text("Replacement policy", encoding="utf-8")
    repository.fail_replacements.add("sensitive/policy.md")
    report = service.scan(trigger="manual")

    assert report.failed == 1
    assert repository.sources["sensitive/policy.md"].content_hash == original_hash
    assert repository.sources["sensitive/policy.md"].chunks[0].text == "Original policy"


def test_scan_commits_prepared_index_only_after_metadata_replace(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("中文公开答案", encoding="utf-8")
    repository = InMemoryScanRepository()
    index = FakeKnowledgeIndex()

    report = ScanService(root, repository, knowledge_index=index).scan(trigger="manual")

    assert report.added == 1
    assert index.prepared[0].committed is True
    assert index.prepared[0].rolled_back is False


def test_metadata_failure_rolls_back_prepared_index(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "sensitive" / "policy.md").write_text("敏感规则", encoding="utf-8")
    repository = InMemoryScanRepository()
    repository.fail_replacements.add("sensitive/policy.md")
    index = FakeKnowledgeIndex()

    report = ScanService(root, repository, knowledge_index=index).scan(trigger="manual")

    assert report.failed == 1
    assert index.prepared[0].committed is False
    assert index.prepared[0].rolled_back is True


def test_deleted_source_is_removed_from_index_before_metadata(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    path = root / "sensitive" / "policy.md"
    path.write_text("敏感规则", encoding="utf-8")
    repository = InMemoryScanRepository()
    index = FakeKnowledgeIndex()
    service = ScanService(root, repository, knowledge_index=index)
    service.scan(trigger="manual")

    path.unlink()
    report = service.scan(trigger="manual")

    assert report.deleted == 1
    assert index.deleted == [("sensitive", "sensitive/policy.md")]


def test_manual_scan_api_starts_in_background_and_returns_a_report(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("API answer", encoding="utf-8")
    service = ScanService(root, InMemoryScanRepository())
    client = TestClient(create_app(scan_service=service))

    started = client.post("/admin/scans")
    fetched = client.get(f"/admin/scans/{started.json()['id']}")

    assert started.status_code == 202
    assert started.json()["trigger"] == "manual"
    assert started.json()["status"] == "running"
    assert started.json()["added"] == 0
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "succeeded"
    assert fetched.json()["added"] == 1


def test_manual_scan_api_reuses_running_scan(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    repository = InMemoryScanRepository()
    service = ScanService(root, repository)
    client = TestClient(create_app(scan_service=service))

    running, started = service.start_scan(trigger="manual")
    duplicate = client.post("/admin/scans")

    assert started is True
    assert duplicate.status_code == 202
    assert duplicate.json()["id"] == str(running.id)
    assert duplicate.json()["status"] == "running"


def test_scan_api_returns_not_found_for_unknown_run(tmp_path: Path) -> None:
    service = ScanService(make_root(tmp_path), InMemoryScanRepository())
    client = TestClient(create_app(scan_service=service))

    response = client.get("/admin/scans/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
