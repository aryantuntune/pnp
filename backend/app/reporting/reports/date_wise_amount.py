"""
Date-wise Amount report.

Returns total revenue per date, broken down by POS and Portal.
Follows the foundation architecture strictly:
  - get_source_flags  → decides which legs to execute
  - apply_pos_filters / apply_portal_filters → WHERE clauses
  - merge_by_key      → combines POS + Portal rows
  - sort_by_date      → output ordering
"""
from __future__ import annotations

import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.ticket import Ticket
from app.reporting.filters import ReportFilters, get_source_flags
from app.reporting.merge import merge_by_key
from app.reporting.query_helpers import apply_portal_filters, apply_pos_filters
from app.reporting.sorting import sort_by_date


# ── Public entry point ────────────────────────────────────────────────────────


async def get_date_wise_amount(
    db: AsyncSession,
    filters: ReportFilters,
) -> dict:
    """
    Date-wise Amount report.

    Parameters
    ----------
    db      : Async SQLAlchemy session.
    filters : ReportFilters — controls date range, branch, route,
              payment mode, and data source (POS / PORTAL / ALL).

    Returns
    -------
    {
        "rows": [
            {
                "date":          datetime.date,
                "pos_amount":    Decimal,
                "portal_amount": Decimal,
                "total_amount":  Decimal,
            },
            ...
        ],
        "grand_total": Decimal,
    }

    Rows are sorted ascending by date.
    Cancelled POS tickets and non-CONFIRMED Portal bookings are excluded.
    """
    include_pos, include_portal = get_source_flags(filters)

    pos_data: list[dict] = []
    if include_pos:
        pos_data = await _query_pos(db, filters)

    portal_data: list[dict] = []
    if include_portal:
        portal_data = await _query_portal(db, filters)

    return _build_date_wise_amount_result(pos_data, portal_data)


# ── DB query legs ─────────────────────────────────────────────────────────────


async def _query_pos(db: AsyncSession, filters: ReportFilters) -> list[dict]:
    """
    Query POS tickets grouped by ticket_date.

    apply_pos_filters adds:
      - Ticket.is_cancelled == False   (mandatory guard)
      - ticket_date range
      - optional branch / route / payment_mode filters
    """
    q = (
        select(
            Ticket.ticket_date.label("date"),
            func.coalesce(func.sum(Ticket.net_amount), 0).label("pos_amount"),
        )
        .group_by(Ticket.ticket_date)
    )
    q = apply_pos_filters(q, filters)
    rows = (await db.execute(q)).all()
    return [
        {
            "date": r.date,
            "pos_amount": Decimal(str(r.pos_amount)),
            "portal_amount": Decimal("0"),
        }
        for r in rows
    ]


async def _query_portal(db: AsyncSession, filters: ReportFilters) -> list[dict]:
    """
    Query Portal bookings grouped by travel_date.

    apply_portal_filters adds:
      - Booking.status == 'CONFIRMED'  (mandatory guard; never is_cancelled)
      - travel_date range
      - optional branch / route / payment_mode filters
    """
    q = (
        select(
            Booking.travel_date.label("date"),
            func.coalesce(func.sum(Booking.net_amount), 0).label("portal_amount"),
        )
        .group_by(Booking.travel_date)
    )
    q = apply_portal_filters(q, filters)
    rows = (await db.execute(q)).all()
    return [
        {
            "date": r.date,
            "pos_amount": Decimal("0"),
            "portal_amount": Decimal(str(r.portal_amount)),
        }
        for r in rows
    ]


# ── Pure transformation (testable without DB) ─────────────────────────────────


def _build_date_wise_amount_result(
    pos_data: list[dict],
    portal_data: list[dict],
) -> dict:
    """
    Merge POS and Portal date-amount lists into the final report structure.

    Both input lists contain dicts with keys:
      date, pos_amount (Decimal), portal_amount (Decimal)

    After merging by date key, computes total_amount and grand_total.

    Parameters
    ----------
    pos_data    : Rows from _query_pos (or empty list if POS disabled).
    portal_data : Rows from _query_portal (or empty list if Portal disabled).

    Returns
    -------
    {"rows": list[dict], "grand_total": Decimal}
    """
    merged = merge_by_key(pos_data, portal_data, key_fn=lambda r: r["date"])

    rows: list[dict] = []
    for row in merged:
        pos_amount = Decimal(str(row.get("pos_amount", 0)))
        portal_amount = Decimal(str(row.get("portal_amount", 0)))
        rows.append(
            {
                "date": row["date"],
                "pos_amount": pos_amount,
                "portal_amount": portal_amount,
                "total_amount": pos_amount + portal_amount,
            }
        )

    rows = sort_by_date(rows)
    grand_total: Decimal = sum(
        (r["total_amount"] for r in rows), Decimal("0")
    )

    return {"rows": rows, "grand_total": grand_total}
