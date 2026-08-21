"""persist complaint election ownership

Revision ID: 0007_add_complaint_election
Revises: 0006_broadcast_groups_and_logs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_add_complaint_election"
down_revision: Union[str, None] = "0006_broadcast_groups_and_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("complaints")}
    existing_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("complaints")}
    with op.batch_alter_table("complaints", recreate="always") as batch:
        if "election_id" not in existing_columns:
            batch.add_column(sa.Column("election_id", sa.String(length=64), nullable=True))
        batch.create_foreign_key("fk_complaints_election_id", "elections", ["election_id"], ["id"], ondelete="SET NULL")
    if "ix_complaints_election_id" not in existing_indexes:
        op.create_index("ix_complaints_election_id", "complaints", ["election_id"])


def downgrade() -> None:
    op.drop_constraint("fk_complaints_election_id", "complaints", type_="foreignkey")
    op.drop_index("ix_complaints_election_id", table_name="complaints")
    op.drop_column("complaints", "election_id")
