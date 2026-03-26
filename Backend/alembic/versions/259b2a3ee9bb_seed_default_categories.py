"""seed default categories

Revision ID: 259b2a3ee9bb
Revises: b2c3d4e5f6a7
Create Date: 2026-03-26 15:57:19.873176

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '259b2a3ee9bb'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CATEGORIES = [
    ("Tax", "#e03131"),
    ("VAT", "#c2255c"),
    ("Bank Fee", "#9c36b5"),
    ("Insurance", "#6741d9"),
    ("Salary", "#3b5bdb"),
    ("Interest", "#1971c2"),
    ("Currency Conversion", "#0c8599"),
    ("Government", "#099268"),
    ("SaaS", "#2f9e44"),
    ("Infrastructure", "#66a80f"),
    ("Marketing", "#e8590c"),
    ("Legal", "#d6336c"),
    ("Accounting", "#862e9c"),
    ("Office", "#5f3dc4"),
    ("Travel", "#1864ab"),
    ("Telecom", "#0b7285"),
    ("Freelancers", "#087f5b"),
    ("Other", "#868e96"),
]


def upgrade() -> None:
    for name, color in CATEGORIES:
        op.execute(
            sa.text(
                "INSERT INTO categories (id, name, color) VALUES (gen_random_uuid(), :name, :color) ON CONFLICT (name) DO NOTHING"
            ).bindparams(name=name, color=color)
        )


def downgrade() -> None:
    names = [name for name, _ in CATEGORIES]
    op.execute(
        sa.text("DELETE FROM categories WHERE name = ANY(:names)").bindparams(names=names)
    )
