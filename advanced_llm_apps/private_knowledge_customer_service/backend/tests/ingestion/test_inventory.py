from pathlib import Path

import pytest

from app.domain.models import KnowledgePartition
from app.ingestion.fingerprint import fingerprint_file
from app.ingestion.inventory import (
    InvalidKnowledgeRootError,
    SymlinkEscapeError,
    inventory_knowledge_root,
)


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "knowledge"
    (root / "public").mkdir(parents=True)
    (root / "sensitive").mkdir()
    return root


@pytest.mark.parametrize("missing_partition", ["public", "sensitive"])
def test_both_fixed_partitions_are_required(
    tmp_path: Path, missing_partition: str
) -> None:
    root = make_root(tmp_path)
    (root / missing_partition).rmdir()

    with pytest.raises(InvalidKnowledgeRootError, match=missing_partition):
        inventory_knowledge_root(root)


def test_symlink_cannot_escape_knowledge_root(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text("private outside content", encoding="utf-8")
    (root / "public" / "escape.md").symlink_to(outside)

    with pytest.raises(SymlinkEscapeError, match="escape.md"):
        inventory_knowledge_root(root)


def test_inventory_ignores_unsupported_and_hidden_files(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "public" / "guide.md").write_text("guide", encoding="utf-8")
    (root / "public" / "archive.zip").write_bytes(b"zip")
    (root / "public" / ".DS_Store").write_bytes(b"finder")

    entries = inventory_knowledge_root(root)

    assert [entry.relative_path.as_posix() for entry in entries] == ["public/guide.md"]


def test_inventory_assigns_partition_and_sorts_paths(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "sensitive" / "contract.pdf").write_bytes(b"contract")
    (root / "public" / "faq.txt").write_text("faq", encoding="utf-8")

    entries = inventory_knowledge_root(root)

    assert [entry.relative_path.as_posix() for entry in entries] == [
        "public/faq.txt",
        "sensitive/contract.pdf",
    ]
    assert [entry.partition for entry in entries] == [
        KnowledgePartition.PUBLIC,
        KnowledgePartition.SENSITIVE,
    ]


def test_fingerprint_is_deterministic_and_content_sensitive(tmp_path: Path) -> None:
    document = tmp_path / "guide.md"
    document.write_text("version one", encoding="utf-8")

    first = fingerprint_file(document)
    second = fingerprint_file(document)
    document.write_text("version two", encoding="utf-8")
    changed = fingerprint_file(document)

    assert first == second
    assert first.content_hash != changed.content_hash
    assert first.size_bytes == len("version one")
    assert changed.size_bytes == len("version two")
