"""merge_0008_complaint_and_0009_notifications

Revision ID: 5f8c78488462
Revises: 0008_complaint_ownership_details, 0009_app_notification_enrich
Create Date: 2026-08-24 05:57:42.311149+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f8c78488462'
down_revision: Union[str, None] = ('0008_complaint_ownership_details', '0009_app_notification_enrich')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
