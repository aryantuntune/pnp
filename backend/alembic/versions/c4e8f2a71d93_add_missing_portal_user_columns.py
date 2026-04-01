"""add google_id, is_verified, is_active to portal_users

Revision ID: c4e8f2a71d93
Revises: b7a1c3d52e90
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8f2a71d93'
down_revision: Union[str, None] = 'b7a1c3d52e90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text(
        "ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE"
    ))
    conn.execute(sa.text(
        "ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false"
    ))
    conn.execute(sa.text(
        "ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true"
    ))


def downgrade() -> None:
    op.drop_column('portal_users', 'is_active')
    op.drop_column('portal_users', 'is_verified')
    op.drop_column('portal_users', 'google_id')
