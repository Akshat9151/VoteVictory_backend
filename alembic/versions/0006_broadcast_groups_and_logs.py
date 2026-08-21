"""broadcast groups, members, and per-attempt logs

Revision ID: 0006_broadcast_groups_and_logs
Revises: 5ba06aedc5cc
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_broadcast_groups_and_logs"
down_revision: Union[str, None] = "5ba06aedc5cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcast_groups",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("organization_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filter_criteria_snapshot", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=64), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("excluded_no_contact", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcast_groups_organization_id", "broadcast_groups", ["organization_id"])
    op.create_index("ix_broadcast_groups_created_by", "broadcast_groups", ["created_by"])
    op.create_index("ix_broadcast_groups_status", "broadcast_groups", ["status"])

    op.create_table(
        "broadcast_group_members",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("voter_id", sa.String(length=64), nullable=False),
        sa.Column("mobile", sa.String(length=50), nullable=False),
        sa.Column("contact_method", sa.String(length=16), nullable=False),
        sa.Column("voter_name", sa.String(length=255), nullable=False),
        sa.Column("ward", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["broadcast_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_id"], ["voters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcast_group_members_group_id", "broadcast_group_members", ["group_id"])
    op.create_index("ix_broadcast_group_members_voter_id", "broadcast_group_members", ["voter_id"])

    op.create_table(
        "broadcast_logs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("group_id", sa.String(length=64), nullable=False),
        sa.Column("voter_id", sa.String(length=64), nullable=True),
        sa.Column("mobile", sa.String(length=50), nullable=False),
        sa.Column("channel_used", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["broadcast_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_id"], ["voters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcast_logs_group_id", "broadcast_logs", ["group_id"])
    op.create_index("ix_broadcast_logs_voter_id", "broadcast_logs", ["voter_id"])


def downgrade() -> None:
    op.drop_index("ix_broadcast_logs_voter_id", table_name="broadcast_logs")
    op.drop_index("ix_broadcast_logs_group_id", table_name="broadcast_logs")
    op.drop_table("broadcast_logs")
    op.drop_index("ix_broadcast_group_members_voter_id", table_name="broadcast_group_members")
    op.drop_index("ix_broadcast_group_members_group_id", table_name="broadcast_group_members")
    op.drop_table("broadcast_group_members")
    op.drop_index("ix_broadcast_groups_status", table_name="broadcast_groups")
    op.drop_index("ix_broadcast_groups_created_by", table_name="broadcast_groups")
    op.drop_index("ix_broadcast_groups_organization_id", table_name="broadcast_groups")
    op.drop_table("broadcast_groups")
