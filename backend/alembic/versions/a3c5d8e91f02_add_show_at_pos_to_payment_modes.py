"""add show_at_pos to payment_modes

Adds a show_at_pos boolean column to payment_modes. When True the mode
appears in the POS ticket-confirmation payment dropdown. When False it is
hidden from POS (used only by portal / customer-app payments).

All existing rows default to True. The "Online" mode (used exclusively by
the customer portal / CCAvenue gateway) is set to False after the column
is added.

Revision ID: a3c5d8e91f02
Revises: f9a5b3c72d16
Create Date: 2026-03-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c5d8e91f02'
down_revision: str = 'f9a5b3c72d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'payment_modes',
        sa.Column('show_at_pos', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
    )
    # "Online" is only used by the customer portal / payment gateway — hide it from POS
    op.execute(
        "UPDATE payment_modes SET show_at_pos = FALSE WHERE LOWER(description) = 'online'"
    )


def downgrade() -> None:
    op.drop_column('payment_modes', 'show_at_pos')
