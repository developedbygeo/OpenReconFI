"""add deferred invoice status

Revision ID: d65bb5d1f9dc
Revises: 259b2a3ee9bb
Create Date: 2026-04-16 15:04:18.026242

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd65bb5d1f9dc'
down_revision: Union[str, Sequence[str], None] = '259b2a3ee9bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE invoice_status ADD VALUE IF NOT EXISTS 'deferred'")


def downgrade() -> None:
    pass
