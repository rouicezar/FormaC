from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.customer_service.answers import AskService, ProviderRegistry
from app.domain.models import KnowledgePartition
from app.main import create_app
from app.model_providers.base import ModelLocation, ModelRequest
from app.records import InMemoryInteractionRecordRepository
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind
from app.retrieval.search_service import OriginalSearchService


class FakeRetriever:
    def search(self, query, *, identity, num_results=5):
        return EvidencePacket(
            provider="raglite-hybrid",
            matches=(
                EvidenceMatch(
                    citation="chunk-1",
                    source="public/退款政策.md",
                    similarity=0.9,
                    evidence="七个自然日内可退款。",
                    partition=KnowledgePartition.PUBLIC,
                    locator={"line_start": 1, "line_end": 1},
                ),
            ),
        )


@dataclass
class FakeProvider:
    name: str = "ollama"
    location: ModelLocation = ModelLocation.LOCAL

    def generate(self, request: ModelRequest) -> str:
        return "退款期为七个自然日。"


def test_web_search_and_ask_are_recorded_in_unified_admin_records() -> None:
    repository = InMemoryInteractionRecordRepository()
    retriever = FakeRetriever()
    app = create_app(
        search_service=OriginalSearchService(retriever),
        ask_service=AskService(
            retriever=retriever,
            providers=ProviderRegistry({"ollama": FakeProvider()}),
        ),
        records_repository=repository,
    )
    client = TestClient(app)

    assert client.post("/search", json={"query": "退款期限"}).status_code == 200
    assert client.post("/ask", json={"question": "退款期限", "provider": "ollama"}).status_code == 200

    response = client.get("/admin/records")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [record["kind"] for record in payload["records"]] == ["ask", "search"]
    assert {record["channel"] for record in payload["records"]} == {"web"}
    assert payload["records"][0]["answer"] == "退款期为七个自然日。"


def test_admin_records_can_filter_channel_and_kind() -> None:
    repository = InMemoryInteractionRecordRepository()
    repository.record(
        channel="web",
        kind="search",
        requester_id="web-anonymous",
        identity=IdentityKind.EXTERNAL.value,
        query="退款",
        answer=None,
        citations=[],
    )
    repository.record(
        channel="feishu",
        kind="ask",
        requester_id="ou_test",
        identity=IdentityKind.INTERNAL.value,
        query="内部规则",
        answer="内部回答",
        citations=[],
    )
    client = TestClient(create_app(records_repository=repository))

    response = client.get("/admin/records", params={"channel": "feishu", "kind": "ask"})

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["records"][0]["requester_id"] == "ou_test"
