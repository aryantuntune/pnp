"""add is_multi_ticket and generated_at to tickets

Revision ID: e7f8a9b0c1d2
Revises: d4e5f6a7b8c9
Create Date: 2026-04-04 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('is_multi_ticket', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('tickets', sa.Column('generated_at', sa.DateTime(timezone=True), nullable=True))
    # Backfill generated_at from created_at for existing rows
    op.execute("UPDATE tickets SET generated_at = created_at WHERE generated_at IS NULL")


def downgrade() -> None:
    op.drop_column('tickets', 'generated_at')
    op.drop_column('tickets', 'is_multi_ticket')
