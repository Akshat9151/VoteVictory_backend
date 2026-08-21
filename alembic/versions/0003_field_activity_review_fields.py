"""Add submitter and review metadata to field activities."""

from alembic import op
import sqlalchemy as sa

revision = "0003_field_activity_review_fields"
down_revision = "0002_add_user_ward"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("field_activity_logs", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column("field_activity_logs", sa.Column("submitted_by", sa.String(length=64), nullable=True))
    op.add_column("field_activity_logs", sa.Column("submitted_by_role", sa.String(length=30), nullable=True))
    op.add_column("field_activity_logs", sa.Column("reviewed_by", sa.String(length=64), nullable=True))
    op.add_column("field_activity_logs", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("field_activity_logs", sa.Column("rejection_reason", sa.Text(), nullable=True))
    op.execute("UPDATE field_activity_logs SET submitted_by_role = 'VOLUNTEER' WHERE submitted_by_role IS NULL")


def downgrade() -> None:
    op.drop_column("field_activity_logs", "rejection_reason")
    op.drop_column("field_activity_logs", "reviewed_at")
    op.drop_column("field_activity_logs", "reviewed_by")
    op.drop_column("field_activity_logs", "submitted_by_role")
    op.drop_column("field_activity_logs", "submitted_by")
    op.drop_column("field_activity_logs", "title")