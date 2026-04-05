"""add pending fields to tracked_inns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tracked_inns",
        sa.Column("pending_data_hash", sa.String(64), nullable=True),
    )
    op.add_column(
        "tracked_inns",
        sa.Column(
            "pending_raw_response",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "tracked_inns",
        sa.Column(
            "pending_changed_fields",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tracked_inns", "pending_changed_fields")
    op.drop_column("tracked_inns", "pending_raw_response")
    op.drop_column("tracked_inns", "pending_data_hash")
