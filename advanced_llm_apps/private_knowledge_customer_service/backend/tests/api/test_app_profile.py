from fastapi.testclient import TestClient

from app.main import create_app
from app.permissions.identities import IdentityRole, IdentityService, InMemoryIdentityRepository
from app.records import InMemoryInteractionRecordRepository
from app.retrieval.raglite_adapter import IdentityKind


def make_client():
    identities = InMemoryIdentityRepository()
    records = InMemoryInteractionRecordRepository()
    app = create_app(
        identity_service=IdentityService(identities),
        records_repository=records,
    )
    return TestClient(app), identities, records


def test_app_profile_starts_as_anonymous_with_web_record_stats() -> None:
    client, _, records = make_client()
    records.record(
        channel="web",
        kind="search",
        requester_id="web-user-1",
        identity=IdentityKind.EXTERNAL.value,
        query="退款",
        answer=None,
        citations=[{"citation": "a"}],
    )

    response = client.get("/app/profile", params={"requester_id": "web-user-1"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "anonymous"
    assert payload["feishu_bound"] is False
    assert payload["records"]["total"] == 1
    assert payload["visible_scope"] == "公开知识"


def test_app_can_bind_feishu_identity_as_external_and_merge_records() -> None:
    client, identities, records = make_client()
    records.record(
        channel="web",
        kind="search",
        requester_id="web-user-1",
        identity=IdentityKind.EXTERNAL.value,
        query="退款",
        answer=None,
        citations=[],
    )
    records.record(
        channel="feishu",
        kind="ask",
        requester_id="ou_user_1",
        identity=IdentityKind.EXTERNAL.value,
        query="帮助",
        answer="帮助",
        citations=[],
    )

    response = client.post(
        "/app/profile/bind-feishu",
        json={
            "requester_id": "web-user-1",
            "feishu_user_id": "ou_user_1",
            "display_name": "测试用户",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "external"
    assert payload["feishu_bound"] is True
    assert payload["display_name"] == "测试用户"
    assert payload["records"]["total"] == 2
    assert identities.get_by_feishu_id("ou_user_1").role is IdentityRole.EXTERNAL


def test_app_profile_reflects_admin_internal_promotion() -> None:
    client, identities, _ = make_client()
    identity = IdentityService(identities).bind_feishu_identity(
        "ou_internal", display_name="内部用户", actor_id="admin"
    )
    IdentityService(identities).set_role(identity.id, IdentityRole.INTERNAL, actor_id="admin")

    response = client.get(
        "/app/profile",
        params={"requester_id": "web-user-1", "feishu_user_id": "ou_internal"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["role"] == "internal"
    assert payload["feishu_bound"] is True
    assert payload["visible_scope"] == "公开与敏感知识"
