from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.retrieval.raglite_adapter import IdentityKind
from app.retrieval.search_service import OriginalSearchService


router = APIRouter(tags=["原文查询"])


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    identity: IdentityKind = IdentityKind.EXTERNAL
    limit: int = Field(default=10, ge=1, le=20)


class SearchResultResponse(BaseModel):
    citation: str
    source: str
    similarity: float
    evidence: str
    partition: str
    locator: dict[str, Any]


class SearchResponse(BaseModel):
    query: str
    total: int
    results: list[SearchResultResponse]


def get_search_service(request: Request) -> OriginalSearchService:
    service = request.app.state.search_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="原文查询服务尚未配置",
        )
    return service


SearchServiceDependency = Annotated[OriginalSearchService, Depends(get_search_service)]


@router.post("/search", response_model=SearchResponse)
def search_originals(
    payload: SearchRequest,
    service: SearchServiceDependency,
) -> SearchResponse:
    packet = service.search(
        payload.query,
        identity=payload.identity,
        num_results=payload.limit,
    )
    results = [SearchResultResponse(**match.as_payload()) for match in packet.matches]
    return SearchResponse(query=payload.query, total=len(results), results=results)
