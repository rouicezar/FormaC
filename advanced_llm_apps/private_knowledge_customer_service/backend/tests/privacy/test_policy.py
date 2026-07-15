from dataclasses import dataclass

import pytest

from app.domain.models import KnowledgePartition
from app.model_providers.base import ModelLocation, ModelRequest
from app.privacy.policy import PrivacyDecision, PrivacyGateway, decide_privacy
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


def packet(partition: KnowledgePartition, text: str = "知识原文") -> EvidencePacket:
    return EvidencePacket(
        provider="test",
        matches=(
            EvidenceMatch(
                citation="chunk-1",
                source="测试.txt",
                similarity=1.0,
                evidence=text,
                partition=partition,
                locator={"line_start": 1, "line_end": 1},
            ),
        ),
    )


@pytest.mark.parametrize(
    ("partition", "location", "allowed", "expected"),
    [
        (KnowledgePartition.PUBLIC, ModelLocation.CLOUD, False, PrivacyDecision.GENERATE),
        (KnowledgePartition.PUBLIC, ModelLocation.LOCAL, False, PrivacyDecision.GENERATE),
        (KnowledgePartition.SENSITIVE, ModelLocation.LOCAL, False, PrivacyDecision.GENERATE),
        (KnowledgePartition.SENSITIVE, ModelLocation.CLOUD, True, PrivacyDecision.GENERATE),
        (
            KnowledgePartition.SENSITIVE,
            ModelLocation.CLOUD,
            False,
            PrivacyDecision.EXCERPT_ONLY,
        ),
    ],
)
def test_privacy_decision_table(partition, location, allowed, expected) -> None:
    assert (
        decide_privacy(
            packet(partition),
            identity=IdentityKind.INTERNAL,
            model_location=location,
            allow_sensitive_cloud=allowed,
        )
        is expected
    )


def test_external_identity_rejects_sensitive_evidence() -> None:
    with pytest.raises(PermissionError, match="外部身份"):
        decide_privacy(
            packet(KnowledgePartition.SENSITIVE),
            identity=IdentityKind.EXTERNAL,
            model_location=ModelLocation.LOCAL,
            allow_sensitive_cloud=False,
        )


@dataclass
class CapturingProvider:
    location: ModelLocation
    name: str = "capture"
    request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> str:
        self.request = request
        return "模型答案"


def test_sensitive_text_never_enters_cloud_request_when_switch_is_off() -> None:
    secret = "仅内部可见的折扣底价"
    provider = CapturingProvider(ModelLocation.CLOUD)

    answer = PrivacyGateway().answer(
        "最低价格是多少？",
        identity=IdentityKind.INTERNAL,
        provider=provider,
        evidence=packet(KnowledgePartition.SENSITIVE, secret),
        allow_sensitive_cloud=False,
    )

    assert provider.request is None
    assert answer.mode is PrivacyDecision.EXCERPT_ONLY
    assert secret in answer.text
    assert answer.citations[0].locator["line_start"] == 1


def test_public_evidence_is_sent_to_selected_provider() -> None:
    provider = CapturingProvider(ModelLocation.CLOUD)
    answer = PrivacyGateway().answer(
        "退款期多久？",
        identity=IdentityKind.EXTERNAL,
        provider=provider,
        evidence=packet(KnowledgePartition.PUBLIC, "退款期为七天"),
    )

    assert answer.mode is PrivacyDecision.GENERATE
    assert answer.text == "模型答案"
    assert provider.request is not None
    assert "退款期为七天" in provider.request.user


def test_no_evidence_never_calls_model() -> None:
    provider = CapturingProvider(ModelLocation.CLOUD)
    answer = PrivacyGateway().answer(
        "知识库没有的问题",
        identity=IdentityKind.EXTERNAL,
        provider=provider,
        evidence=EvidencePacket(provider="test", matches=()),
    )

    assert answer.mode is PrivacyDecision.EXCERPT_ONLY
    assert "无法依据知识库回答" in answer.text
    assert provider.request is None
