"""add user_id to tracked_inns and request_history

Revision ID: c2d3e4f5a6b7
Revises: b2c3d4e5f6a7
Create Date: 2026-04-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tracked_inns: drop old unique on inn, add user_id, add composite unique
    op.drop_index("ix_tracked_inns_inn", table_name="tracked_inns")
    op.add_column(
        "tracked_inns",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_tracked_inns_inn", "tracked_inns", ["inn"])
    op.create_index("ix_tracked_inns_user_id", "tracked_inns", ["user_id"])
    op.create_unique_constraint(
        "uq_tracked_inns_inn_user", "tracked_inns", ["inn", "user_id"]
    )

    # request_history: add user_id
    op.add_column(
        "request_history",
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_request_history_user_id", "request_history", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_request_history_user_id", table_name="request_history")
    op.drop_column("request_history", "user_id")

    op.drop_constraint("uq_tracked_inns_inn_user", "tracked_inns", type_="unique")
    op.drop_index("ix_tracked_inns_user_id", table_name="tracked_inns")
    op.drop_index("ix_tracked_inns_inn", table_name="tracked_inns")
    op.drop_column("tracked_inns", "user_id")
    op.create_index("ix_tracked_inns_inn", "tracked_inns", ["inn"], unique=True)
