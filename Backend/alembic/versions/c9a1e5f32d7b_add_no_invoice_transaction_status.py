"""Add no_invoice to transaction_status enum.

Revision ID: c9a1e5f32d7b
Revises: b7e2d4f19c3a
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9a1e5f32d7b"
down_revision: Union[str, None] = "b7e2d4f19c3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'no_invoice'")


def downgrade() -> None:
    # Postgres doesn't support removing enum values — would need full enum recreation
    pass
