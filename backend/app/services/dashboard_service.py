from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.route_scope import get_route_branch_ids, needs_route_scope
from app.models.ticket import Ticket
from app.models.boat import Boat
from app.models.branch import Branch
from app.models.payment_mode import PaymentMode

# TYPE_CHECKING import to avoid circular dependency at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.user import User


async def get_dashboard_stats(db: AsyncSession, current_user: User | None = None) -> dict:
    """Return aggregated dashboard statistics.

    For route-scoped users (MANAGER and below), ticket_count and today_revenue
    are filtered to the branches belonging to the user's route.
    """
    today = date.today()

    # Determine branch scope
    branch_ids: tuple[int, int] | None = None
    if current_user and needs_route_scope(current_user) and current_user.route_id:
        branch_ids = await get_route_branch_ids(db, current_user.route_id)

    ticket_count_q = select(func.count()).select_from(Ticket)
    today_revenue_q = select(func.coalesce(func.sum(Ticket.net_amount), 0)).where(
        Ticket.ticket_date == today
    )

    # Apply branch scope to ticket queries
    if branch_ids:
        ticket_count_q = ticket_count_q.where(Ticket.branch_id.in_(branch_ids))
        today_revenue_q = today_revenue_q.where(Ticket.branch_id.in_(branch_ids))

    active_ferries_q = select(func.count()).select_from(Boat).where(Boat.is_active == True)  # noqa: E712
    active_branches_q = select(func.count()).select_from(Branch).where(Branch.is_active == True)  # noqa: E712

    # For scoped users, count only their route's branches
    if branch_ids:
        active_branches_q = select(func.count()).select_from(Branch).where(
            Branch.is_active == True,  # noqa: E712
            Branch.id.in_(branch_ids),
        )

    results = await db.execute(ticket_count_q)
    ticket_count = results.scalar() or 0

    results = await db.execute(today_revenue_q)
    today_revenue = float(results.scalar() or 0)

    results = await db.execute(active_ferries_q)
    active_ferries = results.scalar() or 0

    results = await db.execute(active_branches_q)
    active_branches = results.scalar() or 0

    return {
        "ticket_count": ticket_count,
        "today_revenue": today_revenue,
        "active_ferries": active_ferries,
        "active_branches": active_branches,
    }


async def get_today_summary(db: AsyncSession, current_user: User | None = None) -> dict:
    """Return today's ticket summary grouped by branch and payment mode.

    For route-scoped users, results are filtered to their route's branches.
    """
    today = date.today()

    # Determine branch scope
    branch_ids: tuple[int, int] | None = None
    if current_user and needs_route_scope(current_user) and current_user.route_id:
        branch_ids = await get_route_branch_ids(db, current_user.route_id)

    # Revenue expression: sum net_amount only for non-cancelled tickets
    revenue_expr = func.coalesce(
        func.sum(
            case(
                (Ticket.is_cancelled == False, Ticket.net_amount),  # noqa: E712
                else_=0,
            )
        ),
        0,
    )

    # --- Branch breakdown ---
    branch_q = (
        select(
            Ticket.branch_id,
            Branch.name.label("branch_name"),
            func.count().label("ticket_count"),
            revenue_expr.label("revenue"),
        )
        .join(Branch, Ticket.branch_id == Branch.id)
        .where(Ticket.ticket_date == today)
        .group_by(Ticket.branch_id, Branch.name)
    )
    if branch_ids:
        branch_q = branch_q.where(Ticket.branch_id.in_(branch_ids))

    branch_rows = await db.execute(branch_q)
    branches = [
        {
            "branch_id": row.branch_id,
            "branch_name": row.branch_name,
            "ticket_count": row.ticket_count,
            "revenue": Decimal(str(row.revenue)),
        }
        for row in branch_rows.all()
    ]

    # --- Payment mode breakdown ---
    payment_q = (
        select(
            Ticket.payment_mode_id,
            PaymentMode.description.label("payment_mode_name"),
            func.count().label("ticket_count"),
            revenue_expr.label("revenue"),
        )
        .join(PaymentMode, Ticket.payment_mode_id == PaymentMode.id)
        .where(Ticket.ticket_date == today)
        .group_by(Ticket.payment_mode_id, PaymentMode.description)
    )
    if branch_ids:
        payment_q = payment_q.where(Ticket.branch_id.in_(branch_ids))

    payment_rows = await db.execute(payment_q)
    payment_modes = [
        {
            "payment_mode_id": row.payment_mode_id,
            "payment_mode_name": row.payment_mode_name,
            "ticket_count": row.ticket_count,
            "revenue": Decimal(str(row.revenue)),
        }
        for row in payment_rows.all()
    ]

    # --- Totals ---
    total_tickets = sum(b["ticket_count"] for b in branches)
    total_revenue = sum(b["revenue"] for b in branches)

    return {
        "total_tickets": total_tickets,
        "total_revenue": total_revenue,
        "branches": branches,
        "payment_modes": payment_modes,
    }
