"""Allow platform Super Admin saved posters without an organization."""

from alembic import op
import sqlalchemy as sa

revision = "0004_saved_designs_platform_owner"
down_revision = "0003_field_activity_review_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("saved_designs"):
        return

    with op.batch_alter_table("saved_designs") as batch_op:
        batch_op.alter_column("organization_id", nullable=True)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if not inspector.has_table("saved_designs"):
        return

    with op.batch_alter_table("saved_designs") as batch_op:
        batch_op.alter_column("organization_id", nullable=False)