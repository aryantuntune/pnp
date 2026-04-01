"""add_boat_id_and_capacity_columns

Revision ID: f9b34a690fc8
Revises: 6643643aed78
Create Date: 2026-03-31 23:47:31.744559

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9b34a690fc8'
down_revision: Union[str, None] = '6643643aed78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('ferry_schedules', sa.Column('capacity', sa.Integer(), server_default='0', nullable=False))
    op.add_column('tickets', sa.Column('boat_id', sa.Integer(), sa.ForeignKey('boats.id'), nullable=True))


def downgrade() -> None:
    op.drop_column('tickets', 'boat_id')
    op.drop_column('ferry_schedules', 'capacity')
