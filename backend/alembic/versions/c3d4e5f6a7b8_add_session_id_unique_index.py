"""add session_id unique index

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-04-02 23:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_user_sessions_session_id',
        'user_sessions',
        ['session_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_user_sessions_session_id', table_name='user_sessions')
