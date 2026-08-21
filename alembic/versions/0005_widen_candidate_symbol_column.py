"""Widen candidates.symbol column from String(32/50) to String(512) to support image URLs.

Revision ID: 0005_widen_candidate_symbol_column
Revises: 0004_saved_designs_platform_owner
Create Date: 2026-08-20

"""

from alembic import op
import sqlalchemy as sa

revision = "0005_widen_candidate_symbol_column"
down_revision = "0004_saved_designs_platform_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Widen the symbol column to hold full image URLs (same size as photo column)
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.alter_column(
            "symbol",
            existing_type=sa.String(length=50),
            type_=sa.String(length=512),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("candidates") as batch_op:
        batch_op.alter_column(
            "symbol",
            existing_type=sa.String(length=512),
            type_=sa.String(length=50),
            nullable=True,
        )
