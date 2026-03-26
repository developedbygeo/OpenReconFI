"""Add note column to transactions.

Revision ID: f8a2b6c47d9e
Revises: e6c4d8a15f2b
Create Date: 2026-03-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a2b6c47d9e"
down_revision: Union[str, None] = "e6c4d8a15f2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "note")
