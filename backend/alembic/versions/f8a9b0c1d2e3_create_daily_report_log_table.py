"""create daily_report_log table

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-04-03 20:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'daily_report_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('recipient_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default=sa.text("'sending'")),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_date'),
    )


def downgrade() -> None:
    op.drop_table('daily_report_log')
