from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, selectinload

from app.domain.models import IndexStatus, KnowledgeSource
from app.retrieval.evidence import EvidenceMatch


@dataclass(frozen=True, slots=True)
class SqlAlchemySourceLookup:
    engine: Engine

    def get_source(self, relative_path: str) -> tuple[EvidenceMatch, ...]:
        with Session(self.engine) as session:
            source = session.scalar(
                select(KnowledgeSource)
                .where(
                    KnowledgeSource.relative_path == relative_path,
                    KnowledgeSource.index_status != IndexStatus.DELETED,
                )
                .options(selectinload(KnowledgeSource.chunks))
            )
            if source is None:
                return ()
            return tuple(
                EvidenceMatch(
                    citation=f"{source.relative_path}#{chunk.chunk_index}",
                    source=source.relative_path,
                    similarity=1.0,
                    evidence=chunk.content,
                    partition=chunk.partition,
                    locator=chunk.source_locator,
                )
                for chunk in sorted(source.chunks, key=lambda item: item.chunk_index)
            )
