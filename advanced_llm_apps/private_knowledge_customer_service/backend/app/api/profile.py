from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.permissions.identities import IdentityRecord, IdentityRole, IdentityService


router = APIRouter(prefix="/app/profile", tags=["个人身份"])


class ProfileRecordStatsResponse(BaseModel):
    total: int
    search: int
    ask: int
    web: int
    feishu: int
    citations: int


class AppProfileResponse(BaseModel):
    requester_id: str
    feishu_user_id: str | None
    display_name: str
    role: IdentityRole | str
    feishu_bound: bool
    visible_scope: str
    records: ProfileRecordStatsResponse


class BindFeishuProfileRequest(BaseModel):
    requester_id: str = Field(min_length=1, max_length=128)
    feishu_user_id: str = Field(min_length=1, max_length=128)
    display_name: str | None = Field(default=None, max_length=255)


def get_identity_service(request: Request) -> IdentityService:
    service = request.app.state.identity_service
    if service is None:
        raise HTTPException(status_code=503, detail="身份服务尚未配置")
    return service


def get_records_repository(request: Request):
    repository = request.app.state.records_repository
    if repository is None:
        raise HTTPException(status_code=503, detail="个人记录服务尚未配置")
    return repository


IdentityServiceDependency = Annotated[IdentityService, Depends(get_identity_service)]
RecordsRepositoryDependency = Annotated[object, Depends(get_records_repository)]


def _record_stats(repository, requester_ids: list[str]) -> ProfileRecordStatsResponse:
    records = repository.list(requester_ids=requester_ids, limit=100)
    return ProfileRecordStatsResponse(
        total=len(records),
        search=sum(1 for item in records if item.kind == "search"),
        ask=sum(1 for item in records if item.kind == "ask"),
        web=sum(1 for item in records if item.channel == "web"),
        feishu=sum(1 for item in records if item.channel == "feishu"),
        citations=sum(len(item.citations) for item in records),
    )


def _profile(
    *,
    requester_id: str,
    feishu_user_id: str | None,
    display_name: str | None,
    identity: IdentityRecord | None,
    repository,
) -> AppProfileResponse:
    role = identity.role if identity else "anonymous"
    requester_ids = [requester_id]
    if feishu_user_id:
        requester_ids.append(feishu_user_id)
    return AppProfileResponse(
        requester_id=requester_id,
        feishu_user_id=feishu_user_id,
        display_name=display_name or (identity.display_name if identity else None) or "访客",
        role=role,
        feishu_bound=identity is not None,
        visible_scope="公开与敏感知识" if role is IdentityRole.INTERNAL else "公开知识",
        records=_record_stats(repository, requester_ids),
    )


@router.get("", response_model=AppProfileResponse)
def read_profile(
    service: IdentityServiceDependency,
    repository: RecordsRepositoryDependency,
    requester_id: str = Query(min_length=1, max_length=128),
    feishu_user_id: str | None = Query(default=None, min_length=1, max_length=128),
    display_name: str | None = Query(default=None, max_length=255),
) -> AppProfileResponse:
    identity = service.repository.get_by_feishu_id(feishu_user_id) if feishu_user_id else None
    return _profile(
        requester_id=requester_id,
        feishu_user_id=feishu_user_id,
        display_name=display_name,
        identity=identity,
        repository=repository,
    )


@router.post("/bind-feishu", response_model=AppProfileResponse)
def bind_feishu_profile(
    payload: BindFeishuProfileRequest,
    service: IdentityServiceDependency,
    repository: RecordsRepositoryDependency,
) -> AppProfileResponse:
    identity = service.repository.get_by_feishu_id(payload.feishu_user_id)
    if identity is None:
        identity = service.bind_feishu_identity(
            payload.feishu_user_id,
            display_name=payload.display_name,
            actor_id=payload.requester_id,
        )
    return _profile(
        requester_id=payload.requester_id,
        feishu_user_id=payload.feishu_user_id,
        display_name=payload.display_name,
        identity=identity,
        repository=repository,
    )
