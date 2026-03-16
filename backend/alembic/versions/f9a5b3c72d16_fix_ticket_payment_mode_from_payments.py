"""fix ticket payment_mode_id from ticket_payement rows

For tickets that have ticket_payement rows, update tickets.payment_mode_id
to match the payment row with the largest amount.  This corrects historical
data where the frontend always sent CASH as the header payment_mode_id
regardless of the actual payment mode selected by the user.

Revision ID: f9a5b3c72d16
Revises: a1459da85ee6
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f9a5b3c72d16'
down_revision: str = 'a1459da85ee6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # For each ticket that has ticket_payement rows, set payment_mode_id to
    # the payment_mode_id of the payment row with the largest amount.
    # Uses DISTINCT ON to pick one row per ticket ordered by amount DESC.
    op.execute("""
        UPDATE tickets t
        SET    payment_mode_id = sub.payment_mode_id
        FROM (
            SELECT DISTINCT ON (ticket_id)
                   ticket_id,
                   payment_mode_id
            FROM   ticket_payement
            ORDER  BY ticket_id, amount DESC
        ) sub
        WHERE  t.id = sub.ticket_id
          AND  t.payment_mode_id != sub.payment_mode_id
    """)


def downgrade() -> None:
    # Not reversible — original incorrect values are not stored anywhere.
    pass
