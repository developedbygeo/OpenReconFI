"""Add category column to transactions.

Revision ID: d5b3f7a28e1c
Revises: c9a1e5f32d7b
Create Date: 2026-03-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d5b3f7a28e1c"
down_revision: Union[str, None] = "c9a1e5f32d7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("category", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "category")
