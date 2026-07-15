from dataclasses import dataclass, field

import pytest

from app.domain.models import KnowledgePartition
from app.retrieval.raglite_adapter import (
    IdentityKind,
    RagLiteHybridRetriever,
    RetrievalStore,
)


@dataclass
class FakeChunk:
    id: str
    body: str
    metadata_: dict = field(default_factory=dict)


class CapturingRagLite:
    def __init__(self, results: dict[str, tuple[list[str], list[float]]], chunks: dict[str, FakeChunk]):
        self.results = results
        self.chunks = chunks
        self.calls: list[tuple[str, str]] = []

    def has_chunks(self, *, config: object) -> bool:
        self.calls.append(("has_chunks", str(config)))
        return bool(self.results[str(config)][0])

    def hybrid_search(self, query: str, *, num_results: int, config: object):
        self.calls.append(("hybrid_search", str(config)))
        return self.results[str(config)]

    def retrieve_chunks(self, chunk_ids: list[str], *, config: object):
        self.calls.append(("retrieve_chunks", str(config)))
        return [self.chunks[chunk_id] for chunk_id in chunk_ids]

    def rerank_chunks(self, query: str, chunks: list[FakeChunk], *, config: object):
        self.calls.append(("rerank_chunks", str(config)))
        return list(reversed(chunks))


def make_retriever() -> tuple[RagLiteHybridRetriever, CapturingRagLite]:
    api = CapturingRagLite(
        results={
            "public-db": (["pub-1", "pub-2"], [0.7, 0.4]),
            "sensitive-db": (["sec-1"], [0.9]),
        },
        chunks={
            "pub-1": FakeChunk(
                "pub-1",
                "公开退款政策",
                {"source": "public/refund.pdf", "locator": {"page": 2}},
            ),
            "pub-2": FakeChunk(
                "pub-2",
                "公开服务时间",
                {"source": "public/support.xlsx", "locator": {"sheet": "服务时间", "row": 3}},
            ),
            "sec-1": FakeChunk(
                "sec-1",
                "内部折扣底线",
                {"source": "sensitive/pricing.pptx", "locator": {"slide": 4}},
            ),
        },
    )
    retriever = RagLiteHybridRetriever(
        public_store=RetrievalStore(KnowledgePartition.PUBLIC, "public-db"),
        sensitive_store=RetrievalStore(KnowledgePartition.SENSITIVE, "sensitive-db"),
        raglite=api,
    )
    return retriever, api


def test_external_identity_never_routes_to_sensitive_store():
    retriever, api = make_retriever()

    packet = retriever.search("价格", identity=IdentityKind.EXTERNAL)

    assert {config for _, config in api.calls} == {"public-db"}
    assert [match.partition for match in packet.matches] == [KnowledgePartition.PUBLIC] * 2


def test_internal_identity_searches_both_partition_stores_and_keeps_locations():
    retriever, api = make_retriever()

    packet = retriever.search("价格", identity=IdentityKind.INTERNAL)

    assert {config for _, config in api.calls} == {"public-db", "sensitive-db"}
    assert packet.provider == "raglite-hybrid"
    assert [match.citation for match in packet.matches] == ["sec-1", "pub-2", "pub-1"]
    assert packet.matches[0].source == "sensitive/pricing.pptx"
    assert packet.matches[0].locator == {"slide": 4}
    assert packet.matches[1].locator == {"sheet": "服务时间", "row": 3}
    assert packet.matches[2].locator == {"page": 2}


def test_results_are_deterministic_when_rerank_order_ties():
    retriever, _ = make_retriever()

    first = retriever.search("退款", identity=IdentityKind.INTERNAL)
    second = retriever.search("退款", identity=IdentityKind.INTERNAL)

    assert [item.citation for item in first.matches] == [item.citation for item in second.matches]


def test_missing_source_metadata_is_rejected():
    retriever, api = make_retriever()
    api.chunks["pub-1"].metadata_ = {}

    with pytest.raises(ValueError, match="source metadata"):
        retriever.search("退款", identity=IdentityKind.EXTERNAL)


def test_empty_sensitive_store_is_skipped_after_last_document_is_deleted():
    retriever, api = make_retriever()
    api.results["sensitive-db"] = ([], [])

    packet = retriever.search("内部规则", identity=IdentityKind.INTERNAL)

    assert all(match.partition is KnowledgePartition.PUBLIC for match in packet.matches)
    assert ("hybrid_search", "sensitive-db") not in api.calls
