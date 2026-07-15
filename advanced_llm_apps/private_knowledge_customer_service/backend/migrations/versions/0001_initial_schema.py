"""Create the initial private knowledge customer service schema.

Revision ID: 0001
Revises:
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


knowledge_partition = postgresql.ENUM(
    "PUBLIC", "SENSITIVE", name="knowledge_partition", create_type=False
)
index_status = postgresql.ENUM(
    "PENDING", "READY", "FAILED", "DELETED", name="index_status", create_type=False
)
run_status = postgresql.ENUM(
    "RUNNING", "SUCCEEDED", "PARTIAL", "FAILED", name="run_status", create_type=False
)
conversation_state = postgresql.ENUM(
    "BOT_ACTIVE", "HUMAN_OWNED", "CLOSED", name="conversation_state", create_type=False
)
ticket_status = postgresql.ENUM(
    "OPEN", "CLAIMED", "RESOLVED", name="ticket_status", create_type=False
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    for enum_type in (
        knowledge_partition,
        index_status,
        run_status,
        conversation_state,
        ticket_status,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "knowledge_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_root", sa.Text(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("partition", knowledge_partition, nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("modified_at_ns", sa.BigInteger(), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("index_status", index_status, nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_root", "relative_path", name="uq_source_root_relative_path"
        ),
    )
    op.create_index(
        "ix_source_partition_status",
        "knowledge_sources",
        ["partition", "index_status"],
        unique=False,
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("partition", knowledge_partition, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.JSON(), nullable=False),
        sa.Column("embedding", Vector(1024), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "chunk_index", name="uq_source_chunk_index"),
    )
    op.create_index("ix_chunk_partition", "document_chunks", ["partition"], unique=False)

    op.create_table(
        "scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger", sa.String(length=32), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("added_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("deleted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.JSON(), server_default="{}", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "identity_whitelist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feishu_user_id", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("added_by", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("feishu_user_id"),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("external_thread_id", sa.String(length=255), nullable=True),
        sa.Column("requester_id", sa.String(length=128), nullable=False),
        sa.Column("state", conversation_state, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), server_default="[]", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "handoff_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trigger_reason", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("assignee_id", sa.String(length=128), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("secret_ref", sa.String(length=255), nullable=True),
        sa.Column("is_local", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "allow_sensitive_to_cloud", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("object_id", sa.String(length=128), nullable=True),
        sa.Column("result", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), server_default="{}", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_actor_created", "audit_events", ["actor_id", "created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_audit_actor_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("model_configs")
    op.drop_table("handoff_tickets")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("identity_whitelist")
    op.drop_table("scan_runs")
    op.drop_index("ix_chunk_partition", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_index("ix_source_partition_status", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")

    bind = op.get_bind()
    for enum_type in (
        ticket_status,
        conversation_state,
        run_status,
        index_status,
        knowledge_partition,
    ):
        enum_type.drop(bind, checkfirst=True)
