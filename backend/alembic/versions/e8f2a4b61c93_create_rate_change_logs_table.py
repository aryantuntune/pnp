"""create rate_change_logs table

Revision ID: e8f2a4b61c93
Revises: d7e3f1a20b54
Create Date: 2026-03-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e8f2a4b61c93"
down_revision: str = "d7e3f1a20b54"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = 'rate_change_logs'"))
    if result.fetchone():
        return
    op.create_table(
        "rate_change_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.Time(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("old_rate", sa.Numeric(precision=38, scale=2), nullable=True),
        sa.Column("new_rate", sa.Numeric(precision=38, scale=2), nullable=True),
        sa.Column("updated_by_user", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], name="fk_rate_change_logs_route_id"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], name="fk_rate_change_logs_item_id"),
        sa.ForeignKeyConstraint(["updated_by_user"], ["users.id"], name="fk_rate_change_logs_updated_by_user"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rate_change_logs_date", "rate_change_logs", ["date"])
    op.create_index("ix_rate_change_logs_updated_by_user", "rate_change_logs", ["updated_by_user"])


def downgrade() -> None:
    op.drop_index("ix_rate_change_logs_updated_by_user", table_name="rate_change_logs")
    op.drop_index("ix_rate_change_logs_date", table_name="rate_change_logs")
    op.drop_table("rate_change_logs")
