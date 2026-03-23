"""add pgvector, embeddings, chat_messages

Revision ID: a3f5c8e21b4d
Revises: 716a11cb118a
Create Date: 2026-03-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f5c8e21b4d"
down_revision: Union[str, None] = "716a11cb118a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create chat_role enum
    chat_role_enum = postgresql.ENUM("user", "assistant", name="chat_role", create_type=False)
    chat_role_enum.create(op.get_bind(), checkfirst=True)

    # Add embedding columns to invoices and transactions
    op.add_column("invoices", sa.Column("embedding", Vector(1024), nullable=True))
    op.add_column("transactions", sa.Column("embedding", Vector(1024), nullable=True))

    # Create chat_messages table
    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role", postgresql.ENUM("user", "assistant", name="chat_role", create_type=False), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("retrieved_invoice_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("retrieved_tx_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.execute("DROP TYPE IF EXISTS chat_role")
    op.drop_column("transactions", "embedding")
    op.drop_column("invoices", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
