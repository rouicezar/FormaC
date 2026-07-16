from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.domain.models import InteractionRecord


@dataclass(frozen=True, slots=True)
class StoredInteractionRecord:
    id: UUID
    channel: str
    kind: str
    requester_id: str
    identity: str
    query: str
    answer: str | None
    citations: list[dict]
    metadata: dict
    created_at: datetime


class InMemoryInteractionRecordRepository:
    def __init__(self) -> None:
        self.records: list[StoredInteractionRecord] = []

    def record(
        self,
        *,
        channel: str,
        kind: str,
        requester_id: str,
        identity: str,
        query: str,
        answer: str | None,
        citations: list[dict],
        metadata: dict | None = None,
    ) -> StoredInteractionRecord:
        item = StoredInteractionRecord(
            id=uuid4(),
            channel=channel,
            kind=kind,
            requester_id=requester_id,
            identity=identity,
            query=query,
            answer=answer,
            citations=citations,
            metadata=metadata or {},
            created_at=datetime.now(UTC),
        )
        self.records.append(item)
        return item

    def list(
        self,
        *,
        channel: str | None = None,
        kind: str | None = None,
        requester_id: str | None = None,
        requester_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[StoredInteractionRecord]:
        rows = list(reversed(self.records))
        if channel:
            rows = [row for row in rows if row.channel == channel]
        if kind:
            rows = [row for row in rows if row.kind == kind]
        if requester_ids:
            allowed = set(requester_ids)
            rows = [row for row in rows if row.requester_id in allowed]
        if requester_id:
            rows = [row for row in rows if row.requester_id == requester_id]
        return rows[:limit]


class SqlAlchemyInteractionRecordRepository:
    def __init__(self, engine: Engine) -> None:
        self.factory = sessionmaker(bind=engine, expire_on_commit=False)

    @staticmethod
    def _item(row: InteractionRecord) -> StoredInteractionRecord:
        return StoredInteractionRecord(
            id=row.id,
            channel=row.channel,
            kind=row.kind,
            requester_id=row.requester_id,
            identity=row.identity,
            query=row.query,
            answer=row.answer,
            citations=row.citations,
            metadata=row.metadata_,
            created_at=row.created_at,
        )

    def record(
        self,
        *,
        channel: str,
        kind: str,
        requester_id: str,
        identity: str,
        query: str,
        answer: str | None,
        citations: list[dict],
        metadata: dict | None = None,
    ) -> StoredInteractionRecord:
        with self.factory() as session:
            row = InteractionRecord(
                channel=channel,
                kind=kind,
                requester_id=requester_id,
                identity=identity,
                query=query,
                answer=answer,
                citations=citations,
                metadata_=metadata or {},
            )
            session.add(row)
            session.commit()
            return self._item(row)

    def list(
        self,
        *,
        channel: str | None = None,
        kind: str | None = None,
        requester_id: str | None = None,
        requester_ids: list[str] | None = None,
        limit: int = 50,
    ) -> list[StoredInteractionRecord]:
        statement = select(InteractionRecord)
        if channel:
            statement = statement.where(InteractionRecord.channel == channel)
        if kind:
            statement = statement.where(InteractionRecord.kind == kind)
        if requester_ids:
            statement = statement.where(InteractionRecord.requester_id.in_(requester_ids))
        if requester_id:
            statement = statement.where(InteractionRecord.requester_id == requester_id)
        statement = statement.order_by(InteractionRecord.created_at.desc()).limit(limit)
        with self.factory() as session:
            return [self._item(row) for row in session.scalars(statement).all()]
