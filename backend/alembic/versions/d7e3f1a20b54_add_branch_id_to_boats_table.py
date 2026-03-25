"""add branch_id to boats table

Revision ID: d7e3f1a20b54
Revises: a3f1c9d82e47, c5a3b2d19f01
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e3f1a20b54"
down_revision: tuple[str, str] = ("a3f1c9d82e47", "c5a3b2d19f01")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("ALTER TABLE boats ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id)"))


def downgrade() -> None:
    op.drop_constraint("fk_boats_branch_id", "boats", type_="foreignkey")
    op.drop_column("boats", "branch_id")
