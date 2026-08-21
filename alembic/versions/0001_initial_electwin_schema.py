"""Initial ElectWin Database Schema

Revision ID: 0001_initial_electwin
Revises: 
Create Date: 2026-08-18 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_electwin'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Organizations
    op.create_table(
        'organizations',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=128), nullable=False),
        sa.Column('code', sa.String(length=64), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_organizations_slug'), 'organizations', ['slug'], unique=True)
    op.create_index(op.f('ix_organizations_code'), 'organizations', ['code'], unique=True)

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('ward', sa.String(length=150), nullable=True, default='All Wards'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('mfa_secret', sa.String(length=64), nullable=True),
        sa.Column('recovery_codes_json', sa.Text(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, default=0),
        sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)
    op.create_index(op.f('ix_users_phone'), 'users', ['phone'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 3. Candidates
    op.create_table(
        'candidates',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('hindiName', sa.String(length=150), nullable=True),
        sa.Column('post', sa.String(length=100), nullable=False),
        sa.Column('postType', sa.String(length=32), nullable=False, default='sarpanch'),
        sa.Column('constituency', sa.String(length=200), nullable=False),
        sa.Column('symbol', sa.String(length=32), nullable=False),
        sa.Column('symbolName', sa.String(length=100), nullable=False),
        sa.Column('photo', sa.String(length=500), nullable=True),
        sa.Column('slogan', sa.String(length=500), nullable=True),
        sa.Column('votersCount', sa.Integer(), nullable=False, default=0),
        sa.Column('volunteersCount', sa.Integer(), nullable=False, default=0),
        sa.Column('manifesto', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_organization_id'), 'candidates', ['organization_id'], unique=False)

    # 4. Voters
    op.create_table(
        'voters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(length=16), nullable=False),
        sa.Column('ward', sa.String(length=100), nullable=False),
        sa.Column('mobile', sa.String(length=32), nullable=False, default=''),
        sa.Column('channel', sa.String(length=32), nullable=False, default='WhatsApp'),
        sa.Column('consent', sa.String(length=32), nullable=False, default='Verified'),
        sa.Column('source', sa.String(length=100), nullable=False, default='Official Roll'),
        sa.Column('status', sa.String(length=32), nullable=False, default='Valid'),
        sa.Column('house', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_voters_organization_id'), 'voters', ['organization_id'], unique=False)
    op.create_index(op.f('ix_voters_ward'), 'voters', ['ward'], unique=False)
    op.create_index(op.f('ix_voters_mobile'), 'voters', ['mobile'], unique=False)

    # 5. Team Members & Volunteers
    op.create_table(
        'team_members',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, default='Volunteer'),
        sa.Column('roleTitle', sa.String(length=150), nullable=False),
        sa.Column('ward', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, default='Active'),
        sa.Column('votersHandled', sa.Integer(), nullable=False, default=0),
        sa.Column('addedDate', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'volunteers',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=150), nullable=False),
        sa.Column('ward', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=32), nullable=False),
        sa.Column('votersAdded', sa.Integer(), nullable=False, default=0),
        sa.Column('callsMade', sa.Integer(), nullable=False, default=0),
        sa.Column('slipsDistributed', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.String(length=32), nullable=False, default='Active'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Booths
    op.create_table(
        'booths',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('boothNo', sa.String(length=50), nullable=False),
        sa.Column('location', sa.String(length=255), nullable=False),
        sa.Column('incharge', sa.String(length=150), nullable=False),
        sa.Column('voters', sa.Integer(), nullable=False, default=0),
        sa.Column('slips', sa.Integer(), nullable=False, default=0),
        sa.Column('coverage', sa.String(length=32), nullable=False, default='0%'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. Volunteer Voters (Canvassing)
    op.create_table(
        'volunteer_voters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('mobile', sa.String(length=32), nullable=False, default=''),
        sa.Column('house', sa.String(length=200), nullable=False, default=''),
        sa.Column('status', sa.String(length=32), nullable=False, default='Pending'),
        sa.Column('slipHanded', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. Complaints
    op.create_table(
        'complaints',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('ward', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('desc', sa.Text(), nullable=False),
        sa.Column('date', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, default='Open'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. Expenses (EC Statutory limit: 150000)
    op.create_table(
        'expenses',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('category', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('date', sa.String(length=64), nullable=False),
        sa.Column('note', sa.Text(), nullable=False, default=''),
        sa.Column('mode', sa.String(length=50), nullable=False, default='UPI / Online'),
        sa.Column('user', sa.String(length=150), nullable=False),
        sa.Column('receiptUrl', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 10. Delivery Logs
    op.create_table(
        'delivery_logs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('broadcast_id', sa.String(length=64), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('ward', sa.String(length=100), nullable=False),
        sa.Column('mobile', sa.String(length=32), nullable=False),
        sa.Column('route', sa.String(length=32), nullable=False, default='WhatsApp'),
        sa.Column('status', sa.String(length=32), nullable=False, default='Sending'),
        sa.Column('read', sa.String(length=64), nullable=False, default='Delivered ✓✓'),
        sa.Column('time', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 11. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.String(length=100), nullable=True),
        sa.Column('actor_id', sa.String(length=64), nullable=True),
        sa.Column('actor_name', sa.String(length=150), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_organization_id'), 'audit_logs', ['organization_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)

    # 12. Elections
    op.create_table(
        'elections',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, default='planned'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_elections_organization_id'), 'elections', ['organization_id'], unique=False)

    # 13. Design Templates
    op.create_table(
        'design_templates',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('template_type', sa.String(length=100), nullable=False),
        sa.Column('template_json', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_design_templates_organization_id'), 'design_templates', ['organization_id'], unique=False)


def downgrade() -> None:
    op.drop_table('design_templates')
    op.drop_table('elections')
    op.drop_table('audit_logs')
    op.drop_table('delivery_logs')
    op.drop_table('expenses')
    op.drop_table('complaints')
    op.drop_table('volunteer_voters')
    op.drop_table('booths')
    op.drop_table('volunteers')
    op.drop_table('team_members')
    op.drop_table('voters')
    op.drop_table('candidates')
    op.drop_table('users')
    op.drop_table('organizations')
