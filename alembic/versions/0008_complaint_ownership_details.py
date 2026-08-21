"""complaint ownership and detail fields

Revision ID: 0008_complaint_ownership_details
Revises: 0007_add_complaint_election
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0008_complaint_ownership_details"
down_revision: Union[str, None] = "0007_add_complaint_election"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("complaints")}
    with op.batch_alter_table("complaints", recreate="always") as batch:
        if "created_by_user_id" not in existing:
            batch.add_column(sa.Column("created_by_user_id", sa.String(length=64), nullable=True))
        if "title" not in existing:
            batch.add_column(sa.Column("title", sa.String(length=255), nullable=True))
        if "reported_by_phone" not in existing:
            batch.add_column(sa.Column("reported_by_phone", sa.String(length=50), nullable=True))
        batch.create_foreign_key("fk_complaints_created_by_user_id", "users", ["created_by_user_id"], ["id"], ondelete="SET NULL")
    existing_indexes = {index["name"] for index in sa.inspect(bind).get_indexes("complaints")}
    if "ix_complaints_created_by_user_id" not in existing_indexes:
        op.create_index("ix_complaints_created_by_user_id", "complaints", ["created_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_complaints_created_by_user_id", table_name="complaints")
    with op.batch_alter_table("complaints", recreate="always") as batch:
        batch.drop_constraint("fk_complaints_created_by_user_id", type_="foreignkey")
        batch.drop_column("reported_by_phone")
        batch.drop_column("title")
        batch.drop_column("created_by_user_id")
