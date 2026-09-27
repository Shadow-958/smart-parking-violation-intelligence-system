"""add 'historical_import' to complaint_source enum

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-30

"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres requires enum value additions to run outside a transaction
    # block in older versions; Alembic handles this automatically for
    # ALTER TYPE ... ADD VALUE as of recent versions, but if this fails in
    # your environment, run the ALTER TYPE statement manually first.
    op.execute("ALTER TYPE complaint_source ADD VALUE IF NOT EXISTS 'historical_import'")


def downgrade() -> None:
    # Postgres doesn't support removing a single enum value directly.
    # Reverting this migration would require recreating the enum type
    # without 'historical_import' and remapping any rows using it —
    # deliberately not automated here since that's a destructive,
    # data-dependent operation. If you need to roll back, handle it
    # manually with full awareness of what references the value.
    raise NotImplementedError(
        "Downgrading 0003 requires manually recreating the complaint_source "
        "enum without 'historical_import' and remapping any rows using it."
    )
