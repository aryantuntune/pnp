"""merge_heads

Revision ID: 6643643aed78
Revises: a3c5d8e91f02, a9c4d2e81b37
Create Date: 2026-03-31 23:47:27.145265

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6643643aed78'
down_revision: Union[str, None] = ('a3c5d8e91f02', 'a9c4d2e81b37')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
