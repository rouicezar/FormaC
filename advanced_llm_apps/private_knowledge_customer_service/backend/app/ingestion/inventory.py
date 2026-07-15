import os
from dataclasses import dataclass
from pathlib import Path

from app.domain.models import KnowledgePartition
from app.ingestion.fingerprint import FileFingerprint, fingerprint_file


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".md", ".txt", ".xlsx", ".pptx"}


class InvalidKnowledgeRootError(ValueError):
    pass


class SymlinkEscapeError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    absolute_path: Path
    relative_path: Path
    partition: KnowledgePartition
    fingerprint: FileFingerprint


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _validate_partition(root: Path, name: str) -> Path:
    partition = root / name
    if not partition.exists() or not partition.is_dir() or partition.is_symlink():
        raise InvalidKnowledgeRootError(
            f"knowledge root requires a real {name}/ directory"
        )
    return partition


def _contains_hidden_component(path: Path) -> bool:
    return any(part.startswith(".") for part in path.parts)


def inventory_knowledge_root(root: Path) -> list[InventoryEntry]:
    if not root.exists() or not root.is_dir():
        raise InvalidKnowledgeRootError(f"knowledge root does not exist: {root}")

    resolved_root = root.resolve(strict=True)
    partitions = (
        (_validate_partition(resolved_root, "public"), KnowledgePartition.PUBLIC),
        (_validate_partition(resolved_root, "sensitive"), KnowledgePartition.SENSITIVE),
    )
    entries: list[InventoryEntry] = []

    for partition_root, partition in partitions:
        for current_dir, dir_names, file_names in os.walk(
            partition_root, followlinks=False
        ):
            current_path = Path(current_dir)
            for directory_name in tuple(dir_names):
                directory = current_path / directory_name
                relative_directory = directory.relative_to(resolved_root)
                if _contains_hidden_component(relative_directory):
                    dir_names.remove(directory_name)
                    continue
                if directory.is_symlink():
                    target = directory.resolve(strict=True)
                    if not _is_within(target, resolved_root):
                        raise SymlinkEscapeError(
                            f"symlink escapes knowledge root: {relative_directory}"
                        )
                    dir_names.remove(directory_name)

            for file_name in file_names:
                lexical_path = current_path / file_name
                relative_path = lexical_path.relative_to(resolved_root)
                if _contains_hidden_component(relative_path):
                    continue
                if lexical_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                resolved_file = lexical_path.resolve(strict=True)
                if not _is_within(resolved_file, resolved_root):
                    raise SymlinkEscapeError(
                        f"symlink escapes knowledge root: {relative_path}"
                    )
                if not resolved_file.is_file():
                    continue

                entries.append(
                    InventoryEntry(
                        absolute_path=resolved_file,
                        relative_path=relative_path,
                        partition=partition,
                        fingerprint=fingerprint_file(resolved_file),
                    )
                )

    return sorted(entries, key=lambda entry: entry.relative_path.as_posix())
