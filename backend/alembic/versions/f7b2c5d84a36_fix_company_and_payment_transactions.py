"""fix company.active_theme and payment_transactions column names

Revision ID: f7b2c5d84a36
Revises: e6a1b4c93f25
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2c5d84a36'
down_revision: Union[str, None] = 'e6a1b4c93f25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. company.active_theme — model has it, DB doesn't
    conn.execute(sa.text(
        "ALTER TABLE company ADD COLUMN IF NOT EXISTS active_theme VARCHAR(50) DEFAULT 'ocean'"
    ))

    # 2. payment_transactions — production DB has sabpaisa_txn_id / sabpaisa_message
    #    but model expects gateway_txn_id / gateway_message.
    #    Rename if old names exist; skip if already correct.
    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'payment_transactions' AND column_name = 'sabpaisa_txn_id'"
    ))
    if result.fetchone():
        conn.execute(sa.text(
            "ALTER TABLE payment_transactions RENAME COLUMN sabpaisa_txn_id TO gateway_txn_id"
        ))

    result = conn.execute(sa.text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'payment_transactions' AND column_name = 'sabpaisa_message'"
    ))
    if result.fetchone():
        conn.execute(sa.text(
            "ALTER TABLE payment_transactions RENAME COLUMN sabpaisa_message TO gateway_message"
        ))

    # 3. Other missing columns from DDL audit
    # boats.branch_id
    conn.execute(sa.text(
        "ALTER TABLE boats ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id)"
    ))

    # tickets.ref_no
    conn.execute(sa.text(
        "ALTER TABLE tickets ADD COLUMN IF NOT EXISTS ref_no VARCHAR(30)"
    ))

    # ticket_items.vehicle_name
    conn.execute(sa.text(
        "ALTER TABLE ticket_items ADD COLUMN IF NOT EXISTS vehicle_name VARCHAR(60)"
    ))

    # bookings.booking_date
    conn.execute(sa.text(
        "ALTER TABLE bookings ADD COLUMN IF NOT EXISTS booking_date DATE"
    ))

    # refresh_tokens.portal_user_id
    conn.execute(sa.text(
        "ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS portal_user_id INTEGER REFERENCES portal_users(id) ON DELETE CASCADE"
    ))

    # refresh_tokens.user_id — make nullable (portal users use refresh tokens too)
    conn.execute(sa.text(
        "ALTER TABLE refresh_tokens ALTER COLUMN user_id DROP NOT NULL"
    ))

    # portal_users.google_id
    conn.execute(sa.text(
        "ALTER TABLE portal_users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE"
    ))


def downgrade() -> None:
    pass
