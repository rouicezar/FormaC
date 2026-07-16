from datetime import datetime
from dataclasses import asdict
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel


router = APIRouter(tags=["全局记录"])


class InteractionRecordResponse(BaseModel):
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


class InteractionRecordListResponse(BaseModel):
    total: int
    records: list[InteractionRecordResponse]


class PersonalRecordStatsResponse(BaseModel):
    total: int
    search: int
    ask: int
    web: int
    feishu: int
    citations: int


class PersonalRecordListResponse(InteractionRecordListResponse):
    stats: PersonalRecordStatsResponse


def get_records_repository(request: Request):
    repository = request.app.state.records_repository
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="全局记录服务尚未配置",
        )
    return repository


RecordsRepositoryDependency = Annotated[object, Depends(get_records_repository)]


@router.get("/admin/records", response_model=InteractionRecordListResponse)
def list_admin_records(
    repository: RecordsRepositoryDependency,
    channel: Literal["web", "feishu"] | None = Query(default=None),
    kind: Literal["search", "ask"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> InteractionRecordListResponse:
    records = repository.list(channel=channel, kind=kind, limit=limit)
    return InteractionRecordListResponse(
        total=len(records),
        records=[InteractionRecordResponse(**asdict(record)) for record in records],
    )


@router.get("/app/records", response_model=PersonalRecordListResponse)
def list_personal_records(
    repository: RecordsRepositoryDependency,
    requester_id: str = Query(min_length=1, max_length=128),
    feishu_user_id: str | None = Query(default=None, min_length=1, max_length=128),
    kind: Literal["search", "ask"] | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
) -> PersonalRecordListResponse:
    requester_ids = [requester_id]
    if feishu_user_id:
        requester_ids.append(feishu_user_id)
    records = repository.list(requester_ids=requester_ids, kind=kind, limit=limit)
    stats = PersonalRecordStatsResponse(
        total=len(records),
        search=sum(1 for item in records if item.kind == "search"),
        ask=sum(1 for item in records if item.kind == "ask"),
        web=sum(1 for item in records if item.channel == "web"),
        feishu=sum(1 for item in records if item.channel == "feishu"),
        citations=sum(len(item.citations) for item in records),
    )
    return PersonalRecordListResponse(
        total=len(records),
        stats=stats,
        records=[InteractionRecordResponse(**asdict(record)) for record in records],
    )
