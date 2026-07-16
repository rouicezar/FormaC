"""Write canonical scanner chunks through the repository's RAGLite template."""

from dataclasses import dataclass
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable, Protocol
from uuid import uuid4

from app.domain.models import KnowledgePartition
from app.ingestion.chunking import CanonicalChunk
from app.ingestion.inventory import InventoryEntry


@dataclass(frozen=True, slots=True)
class RagLiteStore:
    partition: KnowledgePartition
    config: Any


class RagLiteIndexBackend(Protocol):
    def source_document_ids(self, config: Any, relative_path: str) -> list[str]: ...

    def insert_chunk(
        self,
        config: Any,
        relative_path: str,
        partition: KnowledgePartition,
        chunk: CanonicalChunk,
    ) -> str: ...

    def delete_documents(self, config: Any, document_ids: list[str]) -> None: ...


@dataclass(slots=True)
class PreparedRagLiteUpdate:
    backend: RagLiteIndexBackend
    config: Any
    old_document_ids: list[str]
    new_document_ids: list[str]
    finished: bool = False

    def commit(self) -> None:
        if self.finished:
            return
        self.backend.delete_documents(self.config, self.old_document_ids)
        self.finished = True

    def rollback(self) -> None:
        if self.finished:
            return
        self.backend.delete_documents(self.config, self.new_document_ids)
        self.finished = True


class ImportedRagLiteIndexBackend:
    """Use RAGLite insertion and table models without replacing its algorithms."""

    def source_document_ids(self, config: Any, relative_path: str) -> list[str]:
        from raglite._database import Document, create_database_engine
        from sqlmodel import Session, select

        with Session(create_database_engine(config)) as session:
            documents = session.exec(select(Document)).all()
            return [
                document.id
                for document in documents
                if document.metadata_.get("source") == relative_path
            ]

    def insert_chunk(
        self,
        config: Any,
        relative_path: str,
        partition: KnowledgePartition,
        chunk: CanonicalChunk,
    ) -> str:
        from raglite import insert_document
        from raglite._database import Chunk, Document, create_database_engine
        from sqlmodel import Session, select

        generation = uuid4().hex
        locator_json = json.dumps(chunk.locator, ensure_ascii=False, sort_keys=True)
        proxy_text = (
            f"# {relative_path}\n\n"
            f"{chunk.text}\n\n"
            f"索引标识：{generation}\n"
        )
        with TemporaryDirectory(prefix="pkcs-raglite-") as directory:
            proxy_path = Path(directory) / f"chunk-{chunk.chunk_index}.md"
            proxy_path.write_text(proxy_text, encoding="utf-8")
            document_id = Document.from_path(proxy_path).id
            insert_document(proxy_path, config=config)

        engine = create_database_engine(config)
        with Session(engine) as session:
            document = session.get(Document, document_id)
            if document is None:
                raise RuntimeError(f"RAGLite did not persist document {document_id}")
            document.filename = Path(relative_path).name
            document.metadata_ = {
                "source": relative_path,
                "partition": partition.value,
                "canonical_chunk_index": chunk.chunk_index,
                "locator": chunk.locator,
                "locator_json": locator_json,
            }
            stored_chunks = session.exec(
                select(Chunk).where(Chunk.document_id == document_id)
            ).all()
            if not stored_chunks:
                raise RuntimeError(f"RAGLite did not persist chunks for {document_id}")
            for stored_chunk in stored_chunks:
                stored_chunk.headings = ""
                stored_chunk.body = chunk.text
                stored_chunk.metadata_ = dict(document.metadata_)
                session.add(stored_chunk)
            session.add(document)
            session.commit()
        return document_id

    def delete_documents(self, config: Any, document_ids: list[str]) -> None:
        if not document_ids:
            return
        from raglite._database import Chunk, ChunkEmbedding, Document, create_database_engine
        from sqlalchemy import delete, select
        from sqlmodel import Session

        engine = create_database_engine(config)
        with Session(engine) as session:
            chunk_ids = list(
                session.scalars(
                    select(Chunk.id).where(Chunk.document_id.in_(document_ids))
                )
            )
            if chunk_ids:
                session.exec(
                    delete(ChunkEmbedding).where(ChunkEmbedding.chunk_id.in_(chunk_ids))
                )
                session.exec(delete(Chunk).where(Chunk.id.in_(chunk_ids)))
            session.exec(delete(Document).where(Document.id.in_(document_ids)))
            session.commit()


class RagLiteIndexWriter:
    def __init__(
        self,
        *,
        public_store: RagLiteStore,
        sensitive_store: RagLiteStore,
        backend: RagLiteIndexBackend | None = None,
    ) -> None:
        if public_store.partition is not KnowledgePartition.PUBLIC:
            raise ValueError("public_store must use public partition")
        if sensitive_store.partition is not KnowledgePartition.SENSITIVE:
            raise ValueError("sensitive_store must use sensitive partition")
        self.stores = {
            KnowledgePartition.PUBLIC: public_store,
            KnowledgePartition.SENSITIVE: sensitive_store,
        }
        self.backend = backend or ImportedRagLiteIndexBackend()

    def prepare_replace(
        self,
        entry: InventoryEntry,
        chunks: list[CanonicalChunk],
        on_progress: Callable[[int, int], None] | None = None,
    ) -> PreparedRagLiteUpdate:
        store = self.stores[entry.partition]
        relative_path = entry.relative_path.as_posix()
        old_document_ids = self.backend.source_document_ids(store.config, relative_path)
        new_document_ids: list[str] = []
        try:
            for index, chunk in enumerate(chunks, start=1):
                new_document_ids.append(
                    self.backend.insert_chunk(
                        store.config,
                        relative_path,
                        entry.partition,
                        chunk,
                    )
                )
                if on_progress:
                    on_progress(index, len(chunks))
        except Exception:
            self.backend.delete_documents(store.config, new_document_ids)
            raise
        return PreparedRagLiteUpdate(
            backend=self.backend,
            config=store.config,
            old_document_ids=old_document_ids,
            new_document_ids=new_document_ids,
        )

    def delete_source(
        self,
        partition: KnowledgePartition,
        relative_path: str,
    ) -> None:
        store = self.stores[partition]
        document_ids = self.backend.source_document_ids(store.config, relative_path)
        self.backend.delete_documents(store.config, document_ids)
