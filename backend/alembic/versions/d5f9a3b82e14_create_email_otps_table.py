"""create email_otps table

Revision ID: d5f9a3b82e14
Revises: c4e8f2a71d93
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f9a3b82e14'
down_revision: Union[str, None] = 'c4e8f2a71d93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'email_otps',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('email', sa.String(90), nullable=False),
        sa.Column('otp_hash', sa.String(255), nullable=False),
        sa.Column('purpose', sa.String(20), nullable=False),
        sa.Column('attempts', sa.Integer, nullable=False, server_default='0'),
        sa.Column('is_used', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('email_otps')
