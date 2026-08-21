"""Allow platform Super Admin saved posters without an organization."""

from alembic import op

revision = "0004_saved_designs_platform_owner"
down_revision = "0003_field_activity_review_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("saved_designs") as batch_op:
        batch_op.alter_column("organization_id", nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("saved_designs") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)