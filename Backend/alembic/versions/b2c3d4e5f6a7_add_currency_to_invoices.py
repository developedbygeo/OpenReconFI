"""Add currency column to invoices.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
    )
    # Backfill from raw_extraction for existing invoices
    op.execute("""
        UPDATE invoices
        SET currency = COALESCE(raw_extraction->>'currency', 'EUR')
        WHERE raw_extraction IS NOT NULL
    """)


def downgrade() -> None:
    op.drop_column("invoices", "currency")
