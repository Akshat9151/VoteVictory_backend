"""Create the core field activity tracking tables.

Revision ID: 0002b_create_field_activity_logs
Revises: 0002_add_user_ward
Create Date: 2026-08-21 08:45:00.000000

This migration exists because the application model references
field_activity_logs and volunteer_profiles, but no earlier migration ever
created those tables. The later review-fields migration alters the activity
log table, so this table must exist before it runs.
"""

from alembic import op
import sqlalchemy as sa

revision = "0002b_create_field_activity_logs"
down_revision = "0002_add_user_ward"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("volunteer_profiles"):
        op.create_table(
            "volunteer_profiles",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.String(length=64), nullable=False),
            sa.Column("organization_id", sa.String(length=64), nullable=False),
            sa.Column("volunteer_code", sa.String(length=50), nullable=False),
            sa.Column("profile_photo_url", sa.String(length=512), nullable=True),
            sa.Column("supervisor_id", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["supervisor_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", name="uq_volunteer_profiles_user_id"),
            sa.UniqueConstraint("volunteer_code", name="uq_volunteer_profiles_volunteer_code"),
        )
        op.create_index(op.f("ix_volunteer_profiles_user_id"), "volunteer_profiles", ["user_id"], unique=False)
        op.create_index(op.f("ix_volunteer_profiles_organization_id"), "volunteer_profiles", ["organization_id"], unique=False)
        op.create_index(op.f("ix_volunteer_profiles_supervisor_id"), "volunteer_profiles", ["supervisor_id"], unique=False)

    if not inspector.has_table("field_activity_logs"):
        op.create_table(
            "field_activity_logs",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("volunteer_id", sa.String(length=64), nullable=True),
            sa.Column("volunteer_name", sa.String(length=150), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=True),
            sa.Column("submitted_by", sa.String(length=64), nullable=True),
            sa.Column("submitted_by_role", sa.String(length=30), nullable=False, server_default="VOLUNTEER"),
            sa.Column("ward", sa.String(length=100), nullable=True),
            sa.Column("booth_no", sa.String(length=50), nullable=True),
            sa.Column("activity_type", sa.String(length=100), nullable=False),
            sa.Column("location", sa.String(length=255), nullable=False),
            sa.Column("date_time", sa.String(length=100), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("photo_url", sa.String(length=500), nullable=True),
            sa.Column("voters_contacted", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("slips_distributed", sa.Integer(), nullable=True, server_default="0"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="Submitted"),
            sa.Column("reviewed_by", sa.String(length=64), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["volunteer_id"], ["volunteer_profiles.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_field_activity_logs_submitted_by"), "field_activity_logs", ["submitted_by"], unique=False)
        op.create_index(op.f("ix_field_activity_logs_submitted_by_role"), "field_activity_logs", ["submitted_by_role"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table("field_activity_logs"):
        op.drop_index(op.f("ix_field_activity_logs_submitted_by_role"), table_name="field_activity_logs")
        op.drop_index(op.f("ix_field_activity_logs_submitted_by"), table_name="field_activity_logs")
        op.drop_table("field_activity_logs")

    if inspector.has_table("volunteer_profiles"):
        op.drop_index(op.f("ix_volunteer_profiles_supervisor_id"), table_name="volunteer_profiles")
        op.drop_index(op.f("ix_volunteer_profiles_organization_id"), table_name="volunteer_profiles")
        op.drop_index(op.f("ix_volunteer_profiles_user_id"), table_name="volunteer_profiles")
        op.drop_table("volunteer_profiles")
