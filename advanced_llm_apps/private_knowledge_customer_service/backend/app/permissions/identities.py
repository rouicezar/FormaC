from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.models import AuditEvent, IdentityWhitelist


class IdentityRole(StrEnum):
    EXTERNAL = "external"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    id: UUID
    feishu_user_id: str
    display_name: str | None
    role: IdentityRole
    active: bool
    added_by: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class IdentityAudit:
    id: UUID
    actor_id: str
    action: str
    identity_id: UUID
    details: dict[str, str]
    created_at: datetime


class IdentityRepository(Protocol):
    def list_identities(self) -> list[IdentityRecord]: ...
    def get(self, identity_id: UUID) -> IdentityRecord | None: ...
    def get_by_feishu_id(self, feishu_user_id: str) -> IdentityRecord | None: ...
    def create_external(
        self, feishu_user_id: str, display_name: str | None, actor_id: str
    ) -> IdentityRecord: ...
    def set_role(
        self, identity_id: UUID, role: IdentityRole, actor_id: str
    ) -> IdentityRecord: ...
    def list_audits(self, limit: int = 20) -> list[IdentityAudit]: ...


class InMemoryIdentityRepository:
    def __init__(self) -> None:
        self.identities: dict[UUID, IdentityRecord] = {}
        self.audits: list[IdentityAudit] = []

    def list_identities(self) -> list[IdentityRecord]:
        return sorted(self.identities.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, identity_id: UUID) -> IdentityRecord | None:
        return self.identities.get(identity_id)

    def get_by_feishu_id(self, feishu_user_id: str) -> IdentityRecord | None:
        return next(
            (item for item in self.identities.values() if item.feishu_user_id == feishu_user_id),
            None,
        )

    def create_external(
        self, feishu_user_id: str, display_name: str | None, actor_id: str
    ) -> IdentityRecord:
        now = datetime.now(UTC)
        identity = IdentityRecord(
            id=uuid4(),
            feishu_user_id=feishu_user_id,
            display_name=display_name,
            role=IdentityRole.EXTERNAL,
            active=False,
            added_by=actor_id,
            created_at=now,
            updated_at=now,
        )
        self.identities[identity.id] = identity
        self.audits.append(
            IdentityAudit(
                id=uuid4(), actor_id=actor_id, action="bind_feishu_identity",
                identity_id=identity.id, details={"role": "external"}, created_at=now,
            )
        )
        return identity

    def set_role(
        self, identity_id: UUID, role: IdentityRole, actor_id: str
    ) -> IdentityRecord:
        current = self.identities[identity_id]
        updated = replace(
            current,
            role=role,
            active=role is IdentityRole.INTERNAL,
            updated_at=datetime.now(UTC),
        )
        self.identities[identity_id] = updated
        self.audits.append(
            IdentityAudit(
                id=uuid4(), actor_id=actor_id,
                action=("promote_internal_identity" if role is IdentityRole.INTERNAL else "downgrade_external_identity"),
                identity_id=identity_id,
                details={"before": current.role.value, "after": role.value},
                created_at=updated.updated_at,
            )
        )
        return updated

    def list_audits(self, limit: int = 20) -> list[IdentityAudit]:
        return list(reversed(self.audits[-limit:]))


class SqlAlchemyIdentityRepository:
    def __init__(self, bind: Engine) -> None:
        self.session_factory = sessionmaker(bind=bind, expire_on_commit=False)

    @staticmethod
    def _record(row: IdentityWhitelist) -> IdentityRecord:
        return IdentityRecord(
            id=row.id,
            feishu_user_id=row.feishu_user_id,
            display_name=row.display_name,
            role=IdentityRole.INTERNAL if row.active else IdentityRole.EXTERNAL,
            active=row.active,
            added_by=row.added_by,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def list_identities(self) -> list[IdentityRecord]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(IdentityWhitelist).order_by(IdentityWhitelist.created_at.desc())
            ).all()
            return [self._record(row) for row in rows]

    def get(self, identity_id: UUID) -> IdentityRecord | None:
        with self.session_factory() as session:
            row = session.get(IdentityWhitelist, identity_id)
            return self._record(row) if row else None

    def get_by_feishu_id(self, feishu_user_id: str) -> IdentityRecord | None:
        with self.session_factory() as session:
            row = session.scalar(
                select(IdentityWhitelist).where(
                    IdentityWhitelist.feishu_user_id == feishu_user_id
                )
            )
            return self._record(row) if row else None

    def create_external(
        self, feishu_user_id: str, display_name: str | None, actor_id: str
    ) -> IdentityRecord:
        with self.session_factory() as session:
            row = IdentityWhitelist(
                feishu_user_id=feishu_user_id,
                display_name=display_name,
                added_by=actor_id,
                active=False,
            )
            session.add(row)
            session.flush()
            self._add_audit(session, row.id, actor_id, "bind_feishu_identity", {"role": "external"})
            session.commit()
            return self._record(row)

    def set_role(
        self, identity_id: UUID, role: IdentityRole, actor_id: str
    ) -> IdentityRecord:
        with self.session_factory() as session:
            row = session.get(IdentityWhitelist, identity_id)
            if row is None:
                raise KeyError(identity_id)
            before = IdentityRole.INTERNAL if row.active else IdentityRole.EXTERNAL
            row.active = role is IdentityRole.INTERNAL
            self._add_audit(
                session,
                row.id,
                actor_id,
                "promote_internal_identity" if role is IdentityRole.INTERNAL else "downgrade_external_identity",
                {"before": before.value, "after": role.value},
            )
            session.commit()
            return self._record(row)

    def _add_audit(
        self, session: Session, identity_id: UUID, actor_id: str, action: str, details: dict[str, str]
    ) -> None:
        session.add(
            AuditEvent(
                actor_id=actor_id,
                action=action,
                object_type="identity_whitelist",
                object_id=str(identity_id),
                result="success",
                details=details,
            )
        )

    def list_audits(self, limit: int = 20) -> list[IdentityAudit]:
        with self.session_factory() as session:
            rows = session.scalars(
                select(AuditEvent)
                .where(AuditEvent.object_type == "identity_whitelist")
                .order_by(AuditEvent.created_at.desc())
                .limit(limit)
            ).all()
            return [
                IdentityAudit(
                    id=row.id,
                    actor_id=row.actor_id,
                    action=row.action,
                    identity_id=UUID(row.object_id),
                    details={str(key): str(value) for key, value in row.details.items()},
                    created_at=row.created_at,
                )
                for row in rows
                if row.object_id
            ]


class IdentityService:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository

    def list_identities(self) -> list[IdentityRecord]:
        return self.repository.list_identities()

    def resolve_feishu_role(self, feishu_user_id: str) -> IdentityRole:
        try:
            identity = self.repository.get_by_feishu_id(feishu_user_id)
        except Exception:
            return IdentityRole.EXTERNAL
        return identity.role if identity else IdentityRole.EXTERNAL

    def bind_feishu_identity(
        self, feishu_user_id: str, *, display_name: str | None, actor_id: str
    ) -> IdentityRecord:
        if self.repository.get_by_feishu_id(feishu_user_id):
            raise ValueError("该飞书身份已经绑定")
        return self.repository.create_external(feishu_user_id, display_name, actor_id)

    def set_role(
        self, identity_id: UUID, role: IdentityRole, *, actor_id: str
    ) -> IdentityRecord:
        current = self.repository.get(identity_id)
        if current is None:
            raise LookupError("未找到该飞书身份")
        if current.role is role:
            return current
        return self.repository.set_role(identity_id, role, actor_id)

    def list_audits(self, limit: int = 20) -> list[IdentityAudit]:
        return self.repository.list_audits(limit)
