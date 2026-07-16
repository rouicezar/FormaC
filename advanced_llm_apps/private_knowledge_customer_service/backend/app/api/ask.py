from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.customer_service.answers import AskService
from app.privacy.policy import PrivacyDecision
from app.retrieval.raglite_adapter import IdentityKind


router = APIRouter(tags=["问答"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    identity: IdentityKind = IdentityKind.EXTERNAL
    provider: str = "deepseek"
    allow_sensitive_cloud: bool = False  # compatibility only; server policy is authoritative


class CitationResponse(BaseModel):
    citation: str
    source: str
    similarity: float
    evidence: str
    partition: str
    locator: dict[str, Any]


class AskResponse(BaseModel):
    answer: str
    mode: PrivacyDecision
    citations: list[CitationResponse]


def get_ask_service(request: Request) -> AskService:
    service = request.app.state.ask_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="问答服务尚未配置",
        )
    return service


AskServiceDependency = Annotated[AskService, Depends(get_ask_service)]


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, service: AskServiceDependency, request: Request) -> AskResponse:
    store = request.app.state.configuration_store
    allow_sensitive_cloud = (
        store.snapshot().allow_sensitive_cloud if store is not None else False
    )
    try:
        result = service.ask(
            payload.question,
            identity=payload.identity,
            provider_name=payload.provider,
            allow_sensitive_cloud=allow_sensitive_cloud,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return AskResponse(
        answer=result.text,
        mode=result.mode,
        citations=[CitationResponse(**match.as_payload()) for match in result.citations],
    )
