from pathlib import Path

from fastapi.testclient import TestClient

from app.ingestion.service import InMemoryScanRepository, ScanService
from app.main import create_app


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    return root


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


def test_manual_scan_api_starts_and_returns_a_report(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "faq.txt").write_text("API answer", encoding="utf-8")
    service = ScanService(root, InMemoryScanRepository())
    client = TestClient(create_app(scan_service=service))

    started = client.post("/admin/scans")
    fetched = client.get(f"/admin/scans/{started.json()['id']}")

    assert started.status_code == 201
    assert started.json()["trigger"] == "manual"
    assert started.json()["added"] == 1
    assert fetched.status_code == 200
    assert fetched.json() == started.json()


def test_scan_api_returns_not_found_for_unknown_run(tmp_path: Path) -> None:
    service = ScanService(make_root(tmp_path), InMemoryScanRepository())
    client = TestClient(create_app(scan_service=service))

    response = client.get("/admin/scans/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
