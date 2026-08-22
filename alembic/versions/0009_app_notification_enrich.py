"""Add notification_type, title, link columns to app_notifications

Revision ID: 0009_app_notification_enrich
Revises: 5ba06aedc5cc
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa

revision = '0009_app_notification_enrich'
down_revision = '5ba06aedc5cc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('app_notifications', sa.Column('notification_type', sa.String(50), nullable=True, server_default='general'))
    op.add_column('app_notifications', sa.Column('title', sa.String(255), nullable=True, server_default='Notification'))
    op.add_column('app_notifications', sa.Column('link', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('app_notifications', 'link')
    op.drop_column('app_notifications', 'title')
    op.drop_column('app_notifications', 'notification_type')
