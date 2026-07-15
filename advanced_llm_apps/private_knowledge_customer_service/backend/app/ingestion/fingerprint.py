from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


READ_BLOCK_SIZE = 1024 * 1024


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    content_hash: str
    modified_at_ns: int
    size_bytes: int


def fingerprint_file(path: Path) -> FileFingerprint:
    digest = sha256()
    with path.open("rb") as stream:
        while block := stream.read(READ_BLOCK_SIZE):
            digest.update(block)

    stat = path.stat()
    return FileFingerprint(
        content_hash=digest.hexdigest(),
        modified_at_ns=stat.st_mtime_ns,
        size_bytes=stat.st_size,
    )
