from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.customer_service.answers import AskService, ProviderRegistry
from app.domain.models import KnowledgePartition
from app.main import create_app
from app.model_providers.base import ModelLocation, ModelRequest
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


class FakeRetriever:
    def __init__(self, packet: EvidencePacket) -> None:
        self.packet = packet
        self.identities: list[IdentityKind] = []

    def search(self, query, *, identity, num_results=5):
        self.identities.append(identity)
        return self.packet


@dataclass
class FakeProvider:
    location: ModelLocation
    name: str
    request: ModelRequest | None = None

    def generate(self, request: ModelRequest) -> str:
        self.request = request
        return "依据知识库生成的回答"


def evidence(partition: KnowledgePartition, text: str) -> EvidencePacket:
    return EvidencePacket(
        provider="raglite-hybrid",
        matches=(
            EvidenceMatch(
                citation="c1",
                source="sensitive/内部规则.txt" if partition is KnowledgePartition.SENSITIVE else "public/公开规则.txt",
                similarity=0.9,
                evidence=text,
                partition=partition,
                locator={"line_start": 2, "line_end": 3},
            ),
        ),
    )


def app_with(packet: EvidencePacket, provider: FakeProvider):
    retriever = FakeRetriever(packet)
    service = AskService(
        retriever=retriever,
        providers=ProviderRegistry({provider.name: provider}),
    )
    return create_app(ask_service=service), retriever


def test_public_ask_returns_generated_answer_and_location() -> None:
    provider = FakeProvider(ModelLocation.CLOUD, "deepseek")
    app, retriever = app_with(evidence(KnowledgePartition.PUBLIC, "退款期七天"), provider)

    response = TestClient(app).post(
        "/ask",
        json={"question": "退款期多久？", "provider": "deepseek"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "依据知识库生成的回答"
    assert response.json()["mode"] == "generate"
    assert response.json()["citations"][0]["locator"] == {
        "line_start": 2,
        "line_end": 3,
    }
    assert retriever.identities == [IdentityKind.EXTERNAL]


def test_sensitive_cloud_defaults_to_excerpt_without_model_request() -> None:
    secret = "内部折扣底价为八折"
    provider = FakeProvider(ModelLocation.CLOUD, "deepseek")
    app, retriever = app_with(evidence(KnowledgePartition.SENSITIVE, secret), provider)

    response = TestClient(app).post(
        "/ask",
        json={
            "question": "内部底价是多少？",
            "identity": "internal",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "excerpt_only"
    assert secret in response.json()["answer"]
    assert provider.request is None
    assert retriever.identities == [IdentityKind.INTERNAL]


def test_unconfigured_provider_returns_chinese_error() -> None:
    provider = FakeProvider(ModelLocation.LOCAL, "ollama")
    app, _ = app_with(evidence(KnowledgePartition.PUBLIC, "公开内容"), provider)

    response = TestClient(app).post(
        "/ask",
        json={"question": "问题", "provider": "deepseek"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "模型提供商未配置：deepseek"
