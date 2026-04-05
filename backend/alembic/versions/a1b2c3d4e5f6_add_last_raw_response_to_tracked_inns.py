"""add last_raw_response to tracked_inns

Revision ID: a1b2c3d4e5f6
Revises: 91434a2320ee
Create Date: 2026-04-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "91434a2320ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tracked_inns",
        sa.Column(
            "last_raw_response",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("tracked_inns", "last_raw_response")
