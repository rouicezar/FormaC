import os

import pytest
from sqlalchemy import create_engine, text

from app.permissions.identities import (
    IdentityRole,
    IdentityService,
    SqlAlchemyIdentityRepository,
)


DATABASE_URL = os.getenv("PKCS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="PKCS_TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


def test_identity_role_and_audit_persist_across_repository_sessions() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(
            text("TRUNCATE identity_whitelist, audit_events RESTART IDENTITY CASCADE")
        )
    try:
        first = IdentityService(SqlAlchemyIdentityRepository(engine))
        bound = first.bind_feishu_identity(
            "ou_postgres_acceptance",
            display_name="数据库验收用户",
            actor_id="integration-admin",
        )
        assert bound.role is IdentityRole.EXTERNAL
        first.set_role(bound.id, IdentityRole.INTERNAL, actor_id="integration-admin")

        restarted = IdentityService(SqlAlchemyIdentityRepository(engine))
        persisted = restarted.list_identities()
        audits = restarted.list_audits()
        assert persisted[0].role is IdentityRole.INTERNAL
        assert [event.action for event in audits] == [
            "promote_internal_identity",
            "bind_feishu_identity",
        ]
    finally:
        engine.dispose()
