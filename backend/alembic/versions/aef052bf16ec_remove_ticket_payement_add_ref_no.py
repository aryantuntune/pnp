"""remove_ticket_payement_add_ref_no

Revision ID: aef052bf16ec
Revises: f9a5b3c72d16
Create Date: 2026-03-20 17:00:07.553670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aef052bf16ec'
down_revision: Union[str, None] = 'f9a5b3c72d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Archive existing split-payment data before dropping
    op.execute("""
        CREATE TABLE IF NOT EXISTS ticket_payement_archive AS
        SELECT * FROM ticket_payement
    """)

    # 2. Drop the split-payment table
    op.execute("DROP TABLE IF EXISTS ticket_payement")

    # 3. Add ref_no column to tickets for UPI transaction references
    op.add_column(
        "tickets",
        sa.Column("ref_no", sa.String(30), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tickets", "ref_no")
    # Note: ticket_payement_archive remains but table is not recreated on downgrade
