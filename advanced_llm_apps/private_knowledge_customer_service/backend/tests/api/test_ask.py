from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.customer_service.answers import AskService, ProviderRegistry
from app.domain.models import KnowledgePartition
from app.main import create_app
from app.config import Settings
from app.configuration import ConfigurationStore
from app.model_providers.base import ModelLocation, ModelRequest
from app.model_providers.base import UnavailableProvider
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind


class FakeRetriever:
    def __init__(self, packet: EvidencePacket) -> None:
        self.packet = packet
        self.identities: list[IdentityKind] = []

    def search(self, query, *, identity, num_results=5):
        self.identities.append(identity)
        return self.packet


class FakeSourceLookup:
    def __init__(self, matches: tuple[EvidenceMatch, ...]) -> None:
        self.matches = matches
        self.paths: list[str] = []

    def get_source(self, relative_path: str) -> tuple[EvidenceMatch, ...]:
        self.paths.append(relative_path)
        return self.matches


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


def match(
    text: str,
    *,
    citation: str = "c1",
    source: str = "public/公开规则.txt",
    partition: KnowledgePartition = KnowledgePartition.PUBLIC,
) -> EvidenceMatch:
    return EvidenceMatch(
        citation=citation,
        source=source,
        similarity=0.9,
        evidence=text,
        partition=partition,
        locator={"line_start": 1, "line_end": 1},
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


def test_sensitive_excerpt_does_not_require_cloud_api_key() -> None:
    retriever = FakeRetriever(evidence(KnowledgePartition.SENSITIVE, "内部折扣底价为八折"))
    service = AskService(
        retriever=retriever,
        providers=ProviderRegistry(
            {
                "deepseek": UnavailableProvider(
                    name="deepseek",
                    location=ModelLocation.CLOUD,
                    reason="DeepSeek API 密钥尚未配置",
                )
            }
        ),
    )

    response = TestClient(create_app(ask_service=service)).post(
        "/ask",
        json={
            "question": "内部底价是多少？",
            "identity": "internal",
            "provider": "deepseek",
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "excerpt_only"
    assert "内部折扣底价为八折" in response.json()["answer"]


def test_client_cannot_enable_sensitive_cloud_without_admin_policy(tmp_path) -> None:
    provider = FakeProvider(ModelLocation.CLOUD, "deepseek")
    retriever = FakeRetriever(evidence(KnowledgePartition.SENSITIVE, "内部底价"))
    service = AskService(
        retriever=retriever,
        providers=ProviderRegistry({"deepseek": provider}),
    )
    store = ConfigurationStore(tmp_path / "config.json", Settings())
    client = TestClient(create_app(ask_service=service, configuration_store=store))

    response = client.post(
        "/ask",
        json={
            "question": "底价？",
            "identity": "internal",
            "provider": "deepseek",
            "allow_sensitive_cloud": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "excerpt_only"
    assert provider.request is None


def test_full_text_transcript_request_returns_whole_source_without_model_call() -> None:
    source = "public/09_视频口播稿/_商单视频口播稿/BENQ 280U显示器.md"
    retriever = FakeRetriever(
        EvidencePacket(
            provider="raglite-hybrid",
            matches=(match("片段命中", source=source),),
        )
    )
    source_lookup = FakeSourceLookup(
        (
            match("第一段口播正文", citation=f"{source}#0", source=source),
            match("第二段口播正文", citation=f"{source}#1", source=source),
            match("第三段口播正文", citation=f"{source}#2", source=source),
        )
    )
    provider = FakeProvider(ModelLocation.CLOUD, "deepseek")
    service = AskService(
        retriever=retriever,
        providers=ProviderRegistry({"deepseek": provider}),
        source_lookup=source_lookup,
    )

    response = TestClient(create_app(ask_service=service)).post(
        "/ask",
        json={"question": "帮我显示benq显示器的口播稿", "provider": "deepseek"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["mode"] == "excerpt_only"
    assert source in payload["answer"]
    assert "第一段口播正文" in payload["answer"]
    assert "第二段口播正文" in payload["answer"]
    assert "第三段口播正文" in payload["answer"]
    assert len(payload["citations"]) == 3
    assert source_lookup.paths == [source]
    assert provider.request is None


def test_display_word_inside_monitor_name_does_not_force_full_text_mode() -> None:
    provider = FakeProvider(ModelLocation.CLOUD, "deepseek")
    app, _ = app_with(evidence(KnowledgePartition.PUBLIC, "显示器参数片段"), provider)

    response = TestClient(app).post(
        "/ask",
        json={"question": "BENQ 显示器适合剪辑吗？", "provider": "deepseek"},
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "generate"
    assert provider.request is not None
