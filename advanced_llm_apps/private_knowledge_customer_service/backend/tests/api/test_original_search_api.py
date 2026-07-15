from fastapi.testclient import TestClient

from app.domain.models import KnowledgePartition
from app.main import create_app
from app.retrieval.evidence import EvidenceMatch, EvidencePacket
from app.retrieval.raglite_adapter import IdentityKind
from app.retrieval.search_service import OriginalSearchService


class CapturingRetriever:
    def __init__(self, packet: EvidencePacket) -> None:
        self.packet = packet
        self.calls: list[tuple[str, IdentityKind, int]] = []

    def search(self, query, *, identity, num_results=5):
        self.calls.append((query, identity, num_results))
        return self.packet


def packet(partition: KnowledgePartition = KnowledgePartition.PUBLIC) -> EvidencePacket:
    return EvidencePacket(
        provider="raglite-hybrid",
        matches=(
            EvidenceMatch(
                citation="chunk-1",
                source=(
                    "sensitive/内部规则.txt"
                    if partition is KnowledgePartition.SENSITIVE
                    else "public/退款政策.md"
                ),
                similarity=0.93,
                evidence="客户可在七个自然日内申请退款。",
                partition=partition,
                locator={"line_start": 3, "line_end": 4},
            ),
        ),
    )


def test_original_search_returns_evidence_without_model_configuration() -> None:
    retriever = CapturingRetriever(packet())
    client = TestClient(
        create_app(search_service=OriginalSearchService(retriever=retriever))
    )

    response = client.post("/search", json={"query": "退款期限"})

    assert response.status_code == 200
    assert response.json() == {
        "query": "退款期限",
        "total": 1,
        "results": [
            {
                "citation": "chunk-1",
                "source": "public/退款政策.md",
                "similarity": 0.93,
                "evidence": "客户可在七个自然日内申请退款。",
                "partition": "public",
                "locator": {"line_start": 3, "line_end": 4},
            }
        ],
    }
    assert retriever.calls == [("退款期限", IdentityKind.EXTERNAL, 10)]


def test_internal_search_passes_identity_and_limit_to_retriever() -> None:
    retriever = CapturingRetriever(packet(KnowledgePartition.SENSITIVE))
    client = TestClient(
        create_app(search_service=OriginalSearchService(retriever=retriever))
    )

    response = client.post(
        "/search",
        json={"query": "内部规则", "identity": "internal", "limit": 3},
    )

    assert response.status_code == 200
    assert response.json()["results"][0]["partition"] == "sensitive"
    assert retriever.calls == [("内部规则", IdentityKind.INTERNAL, 3)]


def test_empty_original_search_returns_explicit_empty_result() -> None:
    retriever = CapturingRetriever(EvidencePacket(provider="raglite-hybrid", matches=()))
    client = TestClient(
        create_app(search_service=OriginalSearchService(retriever=retriever))
    )

    response = client.post("/search", json={"query": "不存在的资料"})

    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["results"] == []


def test_search_requires_configured_retrieval_service() -> None:
    response = TestClient(create_app()).post("/search", json={"query": "退款"})

    assert response.status_code == 503
    assert response.json()["detail"] == "原文查询服务尚未配置"
