"""add session tracking columns to users

Revision ID: 8bfe9649daad
Revises: 2d6c867c0759
Create Date: 2026-03-09 19:59:42.678550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8bfe9649daad'
down_revision: Union[str, None] = '2d6c867c0759'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('active_session_id', sa.String(length=36), nullable=True))
    op.add_column('users', sa.Column('session_last_active', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'session_last_active')
    op.drop_column('users', 'active_session_id')
