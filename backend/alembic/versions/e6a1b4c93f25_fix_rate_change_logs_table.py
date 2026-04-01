"""fix rate_change_logs table — ensure all columns exist

Revision ID: e6a1b4c93f25
Revises: d5f9a3b82e14
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6a1b4c93f25'
down_revision: Union[str, None] = 'd5f9a3b82e14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Check if the table exists at all
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = 'public' AND table_name = 'rate_change_logs')"
    ))
    table_exists = result.scalar()

    if not table_exists:
        # Create the full table
        op.create_table(
            'rate_change_logs',
            sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
            sa.Column('date', sa.Date, nullable=False),
            sa.Column('time', sa.Time, nullable=False),
            sa.Column('route_id', sa.Integer, sa.ForeignKey('routes.id'), nullable=False),
            sa.Column('item_id', sa.Integer, sa.ForeignKey('items.id'), nullable=False),
            sa.Column('old_rate', sa.Numeric(38, 2), nullable=True),
            sa.Column('new_rate', sa.Numeric(38, 2), nullable=True),
            sa.Column('updated_by_user', sa.dialects.postgresql.UUID(as_uuid=True),
                       sa.ForeignKey('users.id'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True),
                       server_default=sa.func.now(), nullable=False),
        )
    else:
        # Table exists but may be missing columns — add them safely
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS date DATE"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS time TIME"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS route_id INTEGER REFERENCES routes(id)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS item_id INTEGER REFERENCES items(id)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS old_rate NUMERIC(38,2)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS new_rate NUMERIC(38,2)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS updated_by_user UUID REFERENCES users(id)"
        ))
        conn.execute(sa.text(
            "ALTER TABLE rate_change_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()"
        ))


def downgrade() -> None:
    # Only drop columns we might have added; don't drop the whole table
    pass
