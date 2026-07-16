from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.config import Settings
from app.configuration import ConfigurationStore
from app.model_providers.base import ModelLocation, UnavailableProvider
from app.model_providers.deepseek import DeepSeekProvider
from app.model_providers.ollama import OllamaProvider
from app.domain.models import AuditEvent


router = APIRouter(prefix="/admin/config", tags=["管理配置"])


class KnowledgeConfiguration(BaseModel):
    root: str | None
    public_path: str | None
    sensitive_path: str | None


class ProviderConfiguration(BaseModel):
    model: str
    endpoint: str | None = None
    api_key_configured: bool | None = None


class ModelConfiguration(BaseModel):
    active_provider: Literal["deepseek", "ollama"]
    allow_sensitive_cloud: bool
    deepseek: ProviderConfiguration
    ollama: ProviderConfiguration


class AdminConfigurationResponse(BaseModel):
    knowledge: KnowledgeConfiguration
    models: ModelConfiguration
    audit_recorded: bool = False


class AdminConfigurationUpdate(BaseModel):
    knowledge_root: str | None = None
    active_provider: Literal["deepseek", "ollama"] | None = None
    deepseek_model: str | None = Field(default=None, min_length=1)
    deepseek_api_key: str | None = None
    ollama_model: str | None = Field(default=None, min_length=1)
    ollama_host: str | None = Field(default=None, min_length=1)
    allow_sensitive_cloud: bool | None = None
    confirm_sensitive_cloud: bool = False


def response_from(
    settings: Settings, *, audit_recorded: bool = False
) -> AdminConfigurationResponse:
    root = Path(settings.knowledge_root) if settings.knowledge_root else None
    return AdminConfigurationResponse(
        knowledge=KnowledgeConfiguration(
            root=str(root) if root else None,
            public_path=str(root / "public") if root else None,
            sensitive_path=str(root / "sensitive") if root else None,
        ),
        models=ModelConfiguration(
            active_provider=settings.active_provider,  # type: ignore[arg-type]
            allow_sensitive_cloud=settings.allow_sensitive_cloud,
            deepseek=ProviderConfiguration(
                model=settings.deepseek_model,
                endpoint="https://api.deepseek.com",
                api_key_configured=bool(settings.deepseek_api_key),
            ),
            ollama=ProviderConfiguration(
                model=settings.ollama_model,
                endpoint=settings.ollama_host,
            ),
        ),
        audit_recorded=audit_recorded,
    )


def get_store(request: Request) -> ConfigurationStore:
    store = request.app.state.configuration_store
    if store is None:
        raise HTTPException(status_code=503, detail="配置服务尚未启用")
    return store


@router.get("", response_model=AdminConfigurationResponse)
def read_configuration(request: Request) -> AdminConfigurationResponse:
    return response_from(get_store(request).snapshot())


@router.put("", response_model=AdminConfigurationResponse)
def save_configuration(
    payload: AdminConfigurationUpdate, request: Request
) -> AdminConfigurationResponse:
    store = get_store(request)
    before = store.snapshot()
    if (
        payload.allow_sensitive_cloud is True
        and not before.allow_sensitive_cloud
        and not payload.confirm_sensitive_cloud
    ):
        raise HTTPException(status_code=400, detail="开启敏感内容云端发送前必须二次确认")
    changes = payload.model_dump(exclude_none=True)
    changes.pop("confirm_sensitive_cloud", None)
    settings = store.update(changes)

    audit_recorded = False
    if before.allow_sensitive_cloud != settings.allow_sensitive_cloud:
        runtime = getattr(request.app.state, "runtime", None)
        if runtime is not None:
            runtime.session.add(
                AuditEvent(
                    actor_id="local-super-admin",
                    action="update_sensitive_cloud_policy",
                    object_type="admin_configuration",
                    object_id="sensitive_cloud_policy",
                    result="success",
                    details={
                        "before": before.allow_sensitive_cloud,
                        "after": settings.allow_sensitive_cloud,
                    },
                )
            )
            runtime.session.commit()
            audit_recorded = True

    scan_service = request.app.state.scan_service
    if scan_service is not None and settings.knowledge_root:
        scan_service.knowledge_root = Path(settings.knowledge_root)
    ask_service = request.app.state.ask_service
    if ask_service is not None:
        ask_service.providers.providers["ollama"] = OllamaProvider(
            model=settings.ollama_model,
            host=settings.ollama_host,
        )
        ask_service.providers.providers["deepseek"] = (
            DeepSeekProvider(
                api_key=settings.deepseek_api_key,
                model=settings.deepseek_model,
            )
            if settings.deepseek_api_key
            else UnavailableProvider(
                name="deepseek",
                location=ModelLocation.CLOUD,
                reason="DeepSeek API 密钥尚未配置",
            )
        )
    return response_from(settings, audit_recorded=audit_recorded)
