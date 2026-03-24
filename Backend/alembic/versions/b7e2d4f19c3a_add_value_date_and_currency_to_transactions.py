"""Add value_date and currency fields to transactions.

Revision ID: b7e2d4f19c3a
Revises: a3f5c8e21b4d
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2d4f19c3a"
down_revision: Union[str, None] = "a3f5c8e21b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("value_date", sa.Date(), nullable=True))
    op.add_column("transactions", sa.Column("original_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("transactions", sa.Column("original_currency", sa.String(3), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "original_currency")
    op.drop_column("transactions", "original_amount")
    op.drop_column("transactions", "value_date")
