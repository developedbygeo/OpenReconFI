"""Add withholding to transaction_status enum and category to transactions.

Revision ID: e6c4d8a15f2b
Revises: d5b3f7a28e1c
Create Date: 2026-03-24
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6c4d8a15f2b"
down_revision: Union[str, None] = "d5b3f7a28e1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE transaction_status ADD VALUE IF NOT EXISTS 'withholding'")


def downgrade() -> None:
    pass
