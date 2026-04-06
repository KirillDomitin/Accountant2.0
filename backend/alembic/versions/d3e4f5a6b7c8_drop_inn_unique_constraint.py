"""drop tracked_inns_inn_key unique constraint (replaced by uq_tracked_inns_inn_user)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-06

"""
from typing import Sequence, Union

from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: Union[str, None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("tracked_inns_inn_key", "tracked_inns", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("tracked_inns_inn_key", "tracked_inns", ["inn"])
