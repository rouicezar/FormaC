from dataclasses import dataclass
from enum import StrEnum

from app.domain.models import KnowledgePartition
from app.model_providers.base import ModelLocation, ModelProvider, ModelRequest
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


class PrivacyDecision(StrEnum):
    GENERATE = "generate"
    EXCERPT_ONLY = "excerpt_only"


def decide_privacy(
    evidence: EvidencePacket,
    *,
    identity: IdentityKind,
    model_location: ModelLocation,
    allow_sensitive_cloud: bool,
) -> PrivacyDecision:
    has_sensitive = any(
        match.partition is KnowledgePartition.SENSITIVE for match in evidence.matches
    )
    if identity is IdentityKind.EXTERNAL and has_sensitive:
        raise PermissionError("外部身份不得接收敏感知识")
    if has_sensitive and model_location is ModelLocation.CLOUD and not allow_sensitive_cloud:
        return PrivacyDecision.EXCERPT_ONLY
    return PrivacyDecision.GENERATE


@dataclass(frozen=True, slots=True)
class GuardedAnswer:
    text: str
    mode: PrivacyDecision
    citations: tuple[EvidenceMatch, ...]


class PrivacyGateway:
    """The only boundary allowed to pass retrieved evidence to a model."""

    def answer(
        self,
        question: str,
        *,
        identity: IdentityKind,
        provider: ModelProvider,
        evidence: EvidencePacket,
        allow_sensitive_cloud: bool = False,
    ) -> GuardedAnswer:
        if not evidence.matches:
            return GuardedAnswer(
                text="未检索到可用的知识库原文，无法依据知识库回答。",
                mode=PrivacyDecision.EXCERPT_ONLY,
                citations=(),
            )
        decision = decide_privacy(
            evidence,
            identity=identity,
            model_location=provider.location,
            allow_sensitive_cloud=allow_sensitive_cloud,
        )
        if decision is PrivacyDecision.EXCERPT_ONLY:
            return GuardedAnswer(
                text=self._format_excerpts(evidence),
                mode=decision,
                citations=evidence.matches,
            )

        request = ModelRequest(
            system=(
                "你是企业知识库问答助手。只能依据给定资料回答；资料不足时明确说明。"
                "回答使用简体中文，并在相关表述后标注引用编号。"
            ),
            user=self._build_user_prompt(question, evidence),
        )
        return GuardedAnswer(
            text=provider.generate(request),
            mode=decision,
            citations=evidence.matches,
        )

    @staticmethod
    def _build_user_prompt(question: str, evidence: EvidencePacket) -> str:
        blocks = [f"问题：{question}", "资料："]
        blocks.extend(
            f"[{index}] 来源：{match.source}\n{match.evidence}"
            for index, match in enumerate(evidence.matches, start=1)
        )
        return "\n\n".join(blocks)

    @staticmethod
    def _format_excerpts(evidence: EvidencePacket) -> str:
        if not evidence.matches:
            return "未检索到可用的知识库原文。"
        lines = ["敏感内容云端发送已关闭，以下仅返回本地检索原文："]
        lines.extend(
            f"[{index}] {match.evidence}（来源：{match.source}）"
            for index, match in enumerate(evidence.matches, start=1)
        )
        return "\n\n".join(lines)
