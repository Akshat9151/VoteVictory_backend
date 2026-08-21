"""Create saved_designs table for poster templates and designs.

Revision ID: 0006_create_saved_designs_table
Revises: 0005_widen_candidate_symbol_column
Create Date: 2026-08-21

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_create_saved_designs_table'
down_revision: Union[str, None] = '0005_widen_candidate_symbol_column'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Only create if it does not already exist
    if not inspector.has_table('saved_designs'):
        op.create_table(
            'saved_designs',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('organization_id', sa.String(length=64), nullable=True),
            sa.Column('user_id', sa.String(length=64), nullable=True),
            sa.Column('election_id', sa.String(length=64), nullable=True),
            sa.Column('template_id', sa.String(length=64), nullable=True),
            sa.Column('title', sa.String(length=255), nullable=False),
            sa.Column('form_data', sa.JSON(), nullable=False),
            sa.Column('canvas_json', sa.JSON(), nullable=True),
            sa.Column('preview_image_url', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['election_id'], ['elections.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['template_id'], ['design_templates.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_saved_designs_organization_id'), 'saved_designs', ['organization_id'], unique=False)
        op.create_index(op.f('ix_saved_designs_user_id'), 'saved_designs', ['user_id'], unique=False)
        op.create_index(op.f('ix_saved_designs_election_id'), 'saved_designs', ['election_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_saved_designs_election_id'), table_name='saved_designs')
    op.drop_index(op.f('ix_saved_designs_user_id'), table_name='saved_designs')
    op.drop_index(op.f('ix_saved_designs_organization_id'), table_name='saved_designs')
    op.drop_table('saved_designs')
