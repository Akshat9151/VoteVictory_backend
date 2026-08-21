"""Add free-text ward assignment to users.

Revision ID: 0002_add_user_ward
Revises: 0001_initial_electwin
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_user_ward"
down_revision = "0001_initial_electwin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ward", sa.String(length=150), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "ward")
