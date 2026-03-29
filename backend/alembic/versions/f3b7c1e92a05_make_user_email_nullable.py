"""make user email nullable

Revision ID: f3b7c1e92a05
Revises: aef052bf16ec
Create Date: 2026-03-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b7c1e92a05"
down_revision: Union[str, None] = "aef052bf16ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Note: downgrade will fail if any user has a NULL email
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
