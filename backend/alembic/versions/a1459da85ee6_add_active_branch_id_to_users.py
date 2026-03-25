"""add active_branch_id to users

Revision ID: a1459da85ee6
Revises: e8f2a4b61c93
Create Date: 2026-03-12 14:40:04.947225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1459da85ee6'
down_revision: str = 'e8f2a4b61c93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE users ADD COLUMN IF NOT EXISTS active_branch_id INTEGER REFERENCES branches(id)"))


def downgrade() -> None:
    op.drop_constraint('fk_users_active_branch_id', 'users', type_='foreignkey')
    op.drop_column('users', 'active_branch_id')
