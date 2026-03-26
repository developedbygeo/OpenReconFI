"""Simplify billing_cycle enum (monthly/annual/one_off), add deterministic to confirmed_by.

Revision ID: a1b2c3d4e5f6
Revises: f8a2b6c47d9e
Create Date: 2026-03-25
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f8a2b6c47d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ConfirmedBy: add 'deterministic' ---
    op.execute("ALTER TYPE confirmed_by ADD VALUE IF NOT EXISTS 'deterministic'")

    # --- BillingCycle: migrate to 3 values ---
    # 1. Add 'one_off' to existing enum so we can migrate data
    op.execute("ALTER TYPE billing_cycle ADD VALUE IF NOT EXISTS 'one_off'")

    # Commit the enum changes (ADD VALUE requires its own transaction)
    op.execute("COMMIT")

    # 2. Migrate data
    op.execute("UPDATE vendors SET billing_cycle = 'monthly' WHERE billing_cycle = 'bimonthly'")
    op.execute("UPDATE vendors SET billing_cycle = 'annual' WHERE billing_cycle = 'quarterly'")
    op.execute("UPDATE vendors SET billing_cycle = 'one_off' WHERE billing_cycle = 'irregular'")

    # 3. Recreate enum with only 3 values (rename-old, create-new, cast, drop-old)
    op.execute("ALTER TYPE billing_cycle RENAME TO billing_cycle_old")
    op.execute("CREATE TYPE billing_cycle AS ENUM ('monthly', 'annual', 'one_off')")
    op.execute(
        "ALTER TABLE vendors ALTER COLUMN billing_cycle TYPE billing_cycle "
        "USING billing_cycle::text::billing_cycle"
    )
    op.execute("DROP TYPE billing_cycle_old")


def downgrade() -> None:
    # Recreate the old 5-value enum
    op.execute("ALTER TYPE billing_cycle RENAME TO billing_cycle_new")
    op.execute(
        "CREATE TYPE billing_cycle AS ENUM "
        "('monthly', 'bimonthly', 'quarterly', 'annual', 'irregular')"
    )
    op.execute(
        "ALTER TABLE vendors ALTER COLUMN billing_cycle TYPE billing_cycle "
        "USING billing_cycle::text::billing_cycle"
    )
    op.execute("DROP TYPE billing_cycle_new")

    # Reverse data migration
    op.execute("UPDATE vendors SET billing_cycle = 'irregular' WHERE billing_cycle = 'one_off'")

    # Note: cannot remove enum value from confirmed_by in PostgreSQL
