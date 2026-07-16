"""add persistent Feishu event idempotency and history"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_feishu_events"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feishu_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("sender_id", sa.String(128), nullable=False),
        sa.Column("command", sa.String(32), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index("ix_feishu_events_sender_id", "feishu_events", ["sender_id"])


def downgrade() -> None:
    op.drop_index("ix_feishu_events_sender_id", table_name="feishu_events")
    op.drop_table("feishu_events")
