"""add failed_login_attempts and locked_until to users

Revision ID: b7a1c3d52e90
Revises: f9b34a690fc8
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a1c3d52e90'
down_revision: Union[str, None] = 'f9b34a690fc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER NOT NULL DEFAULT 0"
    ))
    conn.execute(sa.text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ"
    ))


def downgrade() -> None:
    op.drop_column('users', 'locked_until')
    op.drop_column('users', 'failed_login_attempts')
