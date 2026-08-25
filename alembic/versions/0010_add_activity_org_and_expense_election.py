"""Add tenant and election ownership columns.

Revision ID: 0010_activity_org_expense_election
Revises: 5f8c78488462
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010_activity_org_expense_election"
down_revision: Union[str, None] = "5f8c78488462"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "expenses",
        sa.Column("election_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_expenses_election_id", "expenses", ["election_id"], unique=False)
    op.create_foreign_key(
        "fk_expenses_election_id_elections",
        "expenses",
        "elections",
        ["election_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "field_activity_logs",
        sa.Column("organization_id", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_field_activity_logs_organization_id", "field_activity_logs", ["organization_id"], unique=False)
    op.create_foreign_key(
        "fk_field_activity_logs_organization_id_organizations",
        "field_activity_logs",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_field_activity_logs_organization_id_organizations", "field_activity_logs", type_="foreignkey")
    op.drop_index("ix_field_activity_logs_organization_id", table_name="field_activity_logs")
    op.drop_column("field_activity_logs", "organization_id")
    op.drop_constraint("fk_expenses_election_id_elections", "expenses", type_="foreignkey")
    op.drop_index("ix_expenses_election_id", table_name="expenses")
    op.drop_column("expenses", "election_id")
