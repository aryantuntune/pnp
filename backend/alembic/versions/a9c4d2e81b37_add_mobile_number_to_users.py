"""add mobile_number to users

Revision ID: a9c4d2e81b37
Revises: f3b7c1e92a05
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9c4d2e81b37"
down_revision: Union[str, None] = "f3b7c1e92a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mobile_number", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "mobile_number")
