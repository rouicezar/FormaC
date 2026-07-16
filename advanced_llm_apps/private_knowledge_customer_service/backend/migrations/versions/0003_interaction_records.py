"""add unified interaction records"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_interaction_records"
down_revision = "0002_feishu_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "interaction_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("requester_id", sa.String(length=128), nullable=False),
        sa.Column("identity", sa.String(length=32), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interaction_created", "interaction_records", ["created_at"])
    op.create_index("ix_interaction_channel_kind", "interaction_records", ["channel", "kind"])


def downgrade() -> None:
    op.drop_index("ix_interaction_channel_kind", table_name="interaction_records")
    op.drop_index("ix_interaction_created", table_name="interaction_records")
    op.drop_table("interaction_records")
