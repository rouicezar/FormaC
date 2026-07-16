from fastapi.testclient import TestClient

from app.main import create_app
from app.permissions.identities import IdentityService, InMemoryIdentityRepository


def make_client() -> tuple[TestClient, InMemoryIdentityRepository]:
    repository = InMemoryIdentityRepository()
    return TestClient(create_app(identity_service=IdentityService(repository))), repository


def test_admin_can_bind_feishu_identity_as_external() -> None:
    client, repository = make_client()

    response = client.post(
        "/admin/users",
        json={"feishu_user_id": "ou_new", "display_name": "新用户"},
    )

    assert response.status_code == 201
    assert response.json()["role"] == "external"
    assert response.json()["bound"] is True
    assert repository.audits[0].actor_id == "local-super-admin"


def test_admin_can_promote_and_downgrade_with_audit_receipt() -> None:
    client, repository = make_client()
    user_id = client.post(
        "/admin/users", json={"feishu_user_id": "ou_role", "display_name": "权限用户"}
    ).json()["id"]

    promoted = client.put(f"/admin/users/{user_id}/role", json={"role": "internal"})
    downgraded = client.put(f"/admin/users/{user_id}/role", json={"role": "external"})

    assert promoted.status_code == 200
    assert promoted.json() == {"identity": promoted.json()["identity"], "audit_recorded": True}
    assert promoted.json()["identity"]["role"] == "internal"
    assert downgraded.json()["identity"]["role"] == "external"
    assert repository.audits[-1].action == "downgrade_external_identity"


def test_admin_user_list_and_recent_audits_are_real() -> None:
    client, _ = make_client()
    client.post("/admin/users", json={"feishu_user_id": "ou_list", "display_name": "列表用户"})

    users = client.get("/admin/users")
    audits = client.get("/admin/users/audits")

    assert users.status_code == 200
    assert users.json()["total"] == 1
    assert users.json()["external"] == 1
    assert users.json()["internal"] == 0
    assert audits.json()[0]["action"] == "bind_feishu_identity"


def test_missing_identity_returns_chinese_404() -> None:
    client, _ = make_client()

    response = client.put(
        "/admin/users/00000000-0000-0000-0000-000000000000/role",
        json={"role": "internal"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "未找到该飞书身份"
