from app.permissions.identities import (
    IdentityRole,
    IdentityService,
    InMemoryIdentityRepository,
)


def test_feishu_binding_defaults_to_external_and_is_audited() -> None:
    repository = InMemoryIdentityRepository()
    service = IdentityService(repository)

    identity = service.bind_feishu_identity(
        "ou_123",
        display_name="王小明",
        actor_id="local-super-admin",
    )

    assert identity.role is IdentityRole.EXTERNAL
    assert identity.active is False
    assert repository.audits[0].action == "bind_feishu_identity"
    assert repository.audits[0].details["role"] == "external"


def test_only_explicit_admin_change_promotes_and_downgrades_identity() -> None:
    repository = InMemoryIdentityRepository()
    service = IdentityService(repository)
    identity = service.bind_feishu_identity(
        "ou_456", display_name="李明", actor_id="admin-a"
    )

    promoted = service.set_role(identity.id, IdentityRole.INTERNAL, actor_id="admin-a")
    downgraded = service.set_role(identity.id, IdentityRole.EXTERNAL, actor_id="admin-b")

    assert promoted.role is IdentityRole.INTERNAL
    assert downgraded.role is IdentityRole.EXTERNAL
    assert [event.action for event in repository.audits] == [
        "bind_feishu_identity",
        "promote_internal_identity",
        "downgrade_external_identity",
    ]
    assert repository.audits[-1].details == {
        "before": "internal",
        "after": "external",
    }


def test_duplicate_feishu_binding_is_rejected() -> None:
    service = IdentityService(InMemoryIdentityRepository())
    service.bind_feishu_identity("ou_same", display_name=None, actor_id="admin")

    try:
        service.bind_feishu_identity("ou_same", display_name="重复", actor_id="admin")
    except ValueError as error:
        assert str(error) == "该飞书身份已经绑定"
    else:
        raise AssertionError("duplicate binding should fail")


def test_identity_list_includes_external_and_internal_users() -> None:
    service = IdentityService(InMemoryIdentityRepository())
    external = service.bind_feishu_identity("ou_external", display_name="外部", actor_id="admin")
    internal = service.bind_feishu_identity("ou_internal", display_name="内部", actor_id="admin")
    service.set_role(internal.id, IdentityRole.INTERNAL, actor_id="admin")

    result = service.list_identities()

    assert {item.id for item in result} == {external.id, internal.id}
    assert {item.role for item in result} == {IdentityRole.EXTERNAL, IdentityRole.INTERNAL}


def test_unknown_or_failed_feishu_resolution_is_external() -> None:
    repository = InMemoryIdentityRepository()
    service = IdentityService(repository)

    assert service.resolve_feishu_role("ou_unknown") is IdentityRole.EXTERNAL

    repository.get_by_feishu_id = lambda _value: (_ for _ in ()).throw(RuntimeError("lookup failed"))  # type: ignore[method-assign]
    assert service.resolve_feishu_role("ou_failure") is IdentityRole.EXTERNAL
