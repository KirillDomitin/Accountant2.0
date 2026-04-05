"""initial: request_history, tracked_inns, tracking_changes

Revision ID: 91434a2320ee
Revises:
Create Date: 2026-04-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "91434a2320ee"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "request_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inn", sa.String(12), nullable=False),
        sa.Column("org_name", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("success", "error", name="request_status"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_response", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_request_history_inn", "request_history", ["inn"])

    op.create_table(
        "tracked_inns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inn", sa.String(12), nullable=False),
        sa.Column("org_name", sa.String(500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_data_hash", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inn"),
    )
    op.create_index("ix_tracked_inns_inn", "tracked_inns", ["inn"])

    op.create_table(
        "tracking_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracked_inn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "change_description",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tracked_inn_id"], ["tracked_inns.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_tracking_changes_tracked_inn_id",
        "tracking_changes",
        ["tracked_inn_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_tracking_changes_tracked_inn_id", table_name="tracking_changes")
    op.drop_table("tracking_changes")

    op.drop_index("ix_tracked_inns_inn", table_name="tracked_inns")
    op.drop_table("tracked_inns")

    op.drop_index("ix_request_history_inn", table_name="request_history")
    op.drop_table("request_history")

    op.execute("DROP TYPE IF EXISTS request_status")
