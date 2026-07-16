from dataclasses import dataclass
from typing import Protocol

from app.model_providers.base import ModelProvider
from app.privacy.policy import GuardedAnswer, PrivacyDecision, PrivacyGateway
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind

FULL_TEXT_KEYWORDS = (
    "全文",
    "完整",
    "原文",
    "展示",
    "口播稿",
    "稿子",
    "文案",
    "脚本",
)
FULL_TEXT_PHRASES = (
    "帮我显示",
    "显示一下",
    "给我显示",
    "帮我展示",
    "展示一下",
    "给我展示",
)


class Retriever(Protocol):
    def search(
        self,
        query: str,
        *,
        identity: IdentityKind,
        num_results: int = 5,
    ) -> EvidencePacket: ...


class SourceLookup(Protocol):
    def get_source(self, relative_path: str) -> tuple[EvidenceMatch, ...]: ...


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
        source_lookup: SourceLookup | None = None,
        privacy_gateway: PrivacyGateway | None = None,
    ) -> None:
        self.retriever = retriever
        self.providers = providers
        self.source_lookup = source_lookup
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
        if self._should_return_source(question) and evidence.matches and self.source_lookup:
            source = evidence.matches[0].source
            full_matches = self.source_lookup.get_source(source)
            if full_matches:
                return GuardedAnswer(
                    text=self._format_source_answer(source, full_matches),
                    mode=PrivacyDecision.EXCERPT_ONLY,
                    citations=full_matches,
                )
        return self.privacy_gateway.answer(
            question,
            identity=identity,
            provider=self.providers.get(provider_name),
            evidence=evidence,
            allow_sensitive_cloud=allow_sensitive_cloud,
        )

    @staticmethod
    def _should_return_source(question: str) -> bool:
        normalized = question.strip().lower()
        return any(keyword in normalized for keyword in FULL_TEXT_KEYWORDS) or any(
            phrase in normalized for phrase in FULL_TEXT_PHRASES
        )

    @staticmethod
    def _format_source_answer(source: str, matches: tuple[EvidenceMatch, ...]) -> str:
        joined = "\n\n".join(match.evidence for match in matches if match.evidence)
        return f"以下是命中文档 `{source}` 的原文内容：\n\n{joined}"
