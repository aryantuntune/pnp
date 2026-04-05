"""add activity tracking: user_activity_logs table + user_sessions columns

Revision ID: a1b2c3d4e5f7
Revises: f8a9b0c1d2e3
Create Date: 2026-04-05 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = 'f8a9b0c1d2e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add columns to user_sessions ---
    op.add_column('user_sessions', sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id'), nullable=True))
    op.add_column('user_sessions', sa.Column('route_id', sa.Integer(), sa.ForeignKey('routes.id'), nullable=True))
    op.add_column('user_sessions', sa.Column('latitude', sa.Numeric(10, 7), nullable=True))
    op.add_column('user_sessions', sa.Column('longitude', sa.Numeric(10, 7), nullable=True))
    op.add_column('user_sessions', sa.Column('isp', sa.String(150), nullable=True))

    # --- Create user_activity_logs table ---
    op.create_table(
        'user_activity_logs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action_type', sa.String(30), nullable=False),
        sa.Column('metadata', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_activity_logs_session_id', 'user_activity_logs', ['session_id'])
    op.create_index('ix_user_activity_logs_user_id', 'user_activity_logs', ['user_id'])
    op.create_index('ix_user_activity_logs_action_type', 'user_activity_logs', ['action_type'])
    op.create_index('ix_user_activity_logs_created_at', 'user_activity_logs', ['created_at'])
    op.create_index('ix_user_activity_logs_session_action', 'user_activity_logs', ['session_id', 'action_type'])


def downgrade() -> None:
    op.drop_index('ix_user_activity_logs_session_action', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_created_at', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_action_type', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_user_id', table_name='user_activity_logs')
    op.drop_index('ix_user_activity_logs_session_id', table_name='user_activity_logs')
    op.drop_table('user_activity_logs')

    op.drop_column('user_sessions', 'isp')
    op.drop_column('user_sessions', 'longitude')
    op.drop_column('user_sessions', 'latitude')
    op.drop_column('user_sessions', 'route_id')
    op.drop_column('user_sessions', 'branch_id')
