from dataclasses import dataclass
from typing import Protocol

from app.model_providers.base import ModelProvider
from app.privacy.policy import GuardedAnswer, PrivacyGateway
from app.retrieval.evidence import EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


class Retriever(Protocol):
    def search(
        self,
        query: str,
        *,
        identity: IdentityKind,
        num_results: int = 5,
    ) -> EvidencePacket: ...


@dataclass(frozen=True, slots=True)
class ProviderRegistry:
    providers: dict[str, ModelProvider]

    def get(self, name: str) -> ModelProvider:
        try:
            return self.providers[name]
        except KeyError as error:
            raise ValueError(f"模型提供商未配置：{name}") from error


class AskService:
    def __init__(
        self,
        *,
        retriever: Retriever,
        providers: ProviderRegistry,
        privacy_gateway: PrivacyGateway | None = None,
    ) -> None:
        self.retriever = retriever
        self.providers = providers
        self.privacy_gateway = privacy_gateway or PrivacyGateway()

    def ask(
        self,
        question: str,
        *,
        identity: IdentityKind,
        provider_name: str,
        allow_sensitive_cloud: bool = False,
    ) -> GuardedAnswer:
        evidence = self.retriever.search(question, identity=identity)
        return self.privacy_gateway.answer(
            question,
            identity=identity,
            provider=self.providers.get(provider_name),
            evidence=evidence,
            allow_sensitive_cloud=allow_sensitive_cloud,
        )
