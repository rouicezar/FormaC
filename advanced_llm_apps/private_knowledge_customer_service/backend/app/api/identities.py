from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.permissions.identities import (
    IdentityAudit,
    IdentityRecord,
    IdentityRole,
    IdentityService,
)


router = APIRouter(prefix="/admin/users", tags=["用户管理"])


class IdentityResponse(BaseModel):
    id: UUID
    feishu_user_id: str
    display_name: str | None
    role: IdentityRole
    bound: bool = True
    added_by: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_record(cls, record: IdentityRecord) -> "IdentityResponse":
        return cls(
            id=record.id, feishu_user_id=record.feishu_user_id,
            display_name=record.display_name, role=record.role,
            added_by=record.added_by, created_at=record.created_at,
            updated_at=record.updated_at,
        )


class IdentityListResponse(BaseModel):
    total: int
    external: int
    internal: int
    users: list[IdentityResponse]


class BindIdentityRequest(BaseModel):
    feishu_user_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)


class RoleUpdateRequest(BaseModel):
    role: IdentityRole


class RoleUpdateResponse(BaseModel):
    identity: IdentityResponse
    audit_recorded: bool


class IdentityAuditResponse(BaseModel):
    id: UUID
    actor_id: str
    action: str
    identity_id: UUID
    details: dict[str, str]
    created_at: datetime

    @classmethod
    def from_record(cls, record: IdentityAudit) -> "IdentityAuditResponse":
        return cls(
            id=record.id,
            actor_id=record.actor_id,
            action=record.action,
            identity_id=record.identity_id,
            details=record.details,
            created_at=record.created_at,
        )


def get_identity_service(request: Request) -> IdentityService:
    service = request.app.state.identity_service
    if service is None:
        raise HTTPException(status_code=503, detail="身份服务尚未配置")
    return service


IdentityServiceDependency = Annotated[IdentityService, Depends(get_identity_service)]


@router.get("", response_model=IdentityListResponse)
def list_users(service: IdentityServiceDependency) -> IdentityListResponse:
    records = service.list_identities()
    return IdentityListResponse(
        total=len(records),
        external=sum(item.role is IdentityRole.EXTERNAL for item in records),
        internal=sum(item.role is IdentityRole.INTERNAL for item in records),
        users=[IdentityResponse.from_record(item) for item in records],
    )


@router.post("", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
def bind_identity(
    payload: BindIdentityRequest, service: IdentityServiceDependency
) -> IdentityResponse:
    try:
        record = service.bind_feishu_identity(
            payload.feishu_user_id,
            display_name=payload.display_name,
            actor_id="local-super-admin",
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return IdentityResponse.from_record(record)


@router.get("/audits", response_model=list[IdentityAuditResponse])
def list_identity_audits(
    service: IdentityServiceDependency,
) -> list[IdentityAuditResponse]:
    return [IdentityAuditResponse.from_record(item) for item in service.list_audits()]


@router.put("/{identity_id}/role", response_model=RoleUpdateResponse)
def update_role(
    identity_id: UUID,
    payload: RoleUpdateRequest,
    service: IdentityServiceDependency,
) -> RoleUpdateResponse:
    try:
        before = next(
            (item for item in service.list_identities() if item.id == identity_id), None
        )
        record = service.set_role(
            identity_id, payload.role, actor_id="local-super-admin"
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return RoleUpdateResponse(
        identity=IdentityResponse.from_record(record),
        audit_recorded=before is not None and before.role is not record.role,
    )
