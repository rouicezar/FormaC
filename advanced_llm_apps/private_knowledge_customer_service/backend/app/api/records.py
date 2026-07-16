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
