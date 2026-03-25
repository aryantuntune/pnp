"""
Payment Mode Report.

Returns per-payment-mode transaction counts and revenue, broken down by
POS and Portal.  ALL active payment modes appear in the output, even when
they have zero transactions in the requested period.

Foundation helpers used
-----------------------
  get_source_flags         → which legs to execute
  apply_pos_filters        → WHERE clauses for tickets
  apply_portal_filters     → WHERE clauses for bookings
  merge_by_key(skip_sum)   → merge POS + Portal rows without doubling the key
  sort_by_payment_mode     → alphabetical output ordering
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking
from app.models.payment_mode import PaymentMode
from app.models.ticket import Ticket
from app.reporting.filters import ReportFilters, get_source_flags
from app.reporting.merge import merge_by_key
from app.reporting.query_helpers import apply_portal_filters, apply_pos_filters
from app.reporting.sorting import sort_by_payment_mode

# Fields that are integer IDs and must not be summed during merge
_SKIP_SUM = frozenset({"payment_mode_id"})


# ── Public entry point ────────────────────────────────────────────────────────


async def get_payment_mode_report(
    db: AsyncSession,
    filters: ReportFilters,
) -> dict:
    """
    Payment Mode Report.

    Parameters
    ----------
    db      : Async SQLAlchemy session.
    filters : ReportFilters — controls date range, branch, route,
              payment_mode_id (narrow to one mode), and source.

    Returns
    -------
    {
        "rows": [
            {
                "payment_mode_id":   int,
                "payment_mode_name": str,
                "pos_count":         int,
                "pos_amount":        Decimal,
                "portal_count":      int,
                "portal_amount":     Decimal,
                "total_count":       int,
                "total_amount":      Decimal,
            },
            ...
        ],
        "grand_total_count":  int,
        "grand_total_amount": Decimal,
    }

    Rows are sorted alphabetically by payment_mode_name.
    ALL active payment modes appear, even with zero values.
    Cancelled POS tickets and non-CONFIRMED Portal bookings are excluded.
    """
    include_pos, include_portal = get_source_flags(filters)

    pos_data: list[dict] = []
    if include_pos:
        pos_data = await _query_pos(db, filters)

    portal_data: list[dict] = []
    if include_portal:
        portal_data = await _query_portal(db, filters)

    all_modes = await _load_active_payment_modes(db)

    return _build_payment_mode_result(pos_data, portal_data, all_modes)


# ── DB query legs ─────────────────────────────────────────────────────────────


async def _query_pos(db: AsyncSession, filters: ReportFilters) -> list[dict]:
    """
    Query POS tickets grouped by payment_mode_id.

    apply_pos_filters enforces:
      - Ticket.is_cancelled == False
      - ticket_date range + optional branch / route / payment_mode filters
    """
    q = (
        select(
            Ticket.payment_mode_id,
            func.count(Ticket.id).label("pos_count"),
            func.coalesce(func.sum(Ticket.net_amount), 0).label("pos_amount"),
        )
        .group_by(Ticket.payment_mode_id)
    )
    q = apply_pos_filters(q, filters)
    rows = (await db.execute(q)).all()
    return [
        {
            "payment_mode_id": r.payment_mode_id,
            "pos_count": r.pos_count,
            "pos_amount": Decimal(str(r.pos_amount)),
            "portal_count": 0,
            "portal_amount": Decimal("0"),
        }
        for r in rows
    ]


async def _query_portal(db: AsyncSession, filters: ReportFilters) -> list[dict]:
    """
    Query Portal bookings grouped by payment_mode_id.

    apply_portal_filters enforces:
      - Booking.status == 'CONFIRMED'
      - travel_date range + optional branch / route / payment_mode filters
    """
    q = (
        select(
            Booking.payment_mode_id,
            func.count(Booking.id).label("portal_count"),
            func.coalesce(func.sum(Booking.net_amount), 0).label("portal_amount"),
        )
        .group_by(Booking.payment_mode_id)
    )
    q = apply_portal_filters(q, filters)
    rows = (await db.execute(q)).all()
    return [
        {
            "payment_mode_id": r.payment_mode_id,
            "portal_count": r.portal_count,
            "portal_amount": Decimal(str(r.portal_amount)),
            "pos_count": 0,
            "pos_amount": Decimal("0"),
        }
        for r in rows
    ]


async def _load_active_payment_modes(db: AsyncSession) -> dict[int, str]:
    """
    Load all active payment modes as {id: description}.

    These form the authoritative list of rows in the report.  A mode with no
    transactions in the requested period still appears with zero values.
    """
    result = await db.execute(
        select(PaymentMode.id, PaymentMode.description)
        .where(PaymentMode.is_active == True)  # noqa: E712
    )
    return {row.id: row.description for row in result.all()}


# ── Pure transformation (testable without DB) ─────────────────────────────────


def _build_payment_mode_result(
    pos_data: list[dict],
    portal_data: list[dict],
    all_modes: dict[int, str],
) -> dict:
    """
    Build the final report structure from query results and the active mode map.

    Steps
    -----
    1. Merge POS + Portal rows by payment_mode_id (using skip_sum to prevent
       the integer key from being summed during merge).
    2. For every active mode in all_modes, look up the merged row or default
       to zeros — this guarantees all modes appear.
    3. Add payment_mode_name from all_modes.
    4. Compute total_count and total_amount per row.
    5. Sort alphabetically by payment_mode_name.
    6. Compute grand totals.

    Parameters
    ----------
    pos_data    : Output of _query_pos (or [] if POS disabled).
    portal_data : Output of _query_portal (or [] if Portal disabled).
    all_modes   : {payment_mode_id: description} for all active payment modes.

    Returns
    -------
    {"rows": list[dict], "grand_total_count": int, "grand_total_amount": Decimal}
    """
    # Step 1: Merge — skip_sum prevents payment_mode_id from being doubled
    merged = merge_by_key(
        pos_data,
        portal_data,
        key_fn=lambda r: r["payment_mode_id"],
        skip_sum=_SKIP_SUM,
    )
    merged_map: dict[int, dict] = {row["payment_mode_id"]: row for row in merged}

    # Step 2–4: Build output for every active mode (zero-fill missing ones)
    rows: list[dict] = []
    for pm_id, pm_name in all_modes.items():
        row = merged_map.get(pm_id, {})
        pos_count = int(row.get("pos_count", 0))
        pos_amount = Decimal(str(row.get("pos_amount", "0")))
        portal_count = int(row.get("portal_count", 0))
        portal_amount = Decimal(str(row.get("portal_amount", "0")))
        rows.append(
            {
                "payment_mode_id": pm_id,
                "payment_mode_name": pm_name,
                "pos_count": pos_count,
                "pos_amount": pos_amount,
                "portal_count": portal_count,
                "portal_amount": portal_amount,
                "total_count": pos_count + portal_count,
                "total_amount": pos_amount + portal_amount,
            }
        )

    # Step 5: Sort
    rows = sort_by_payment_mode(rows)

    # Step 6: Grand totals
    grand_total_count: int = sum(r["total_count"] for r in rows)
    grand_total_amount: Decimal = sum(
        (r["total_amount"] for r in rows), Decimal("0")
    )

    return {
        "rows": rows,
        "grand_total_count": grand_total_count,
        "grand_total_amount": grand_total_amount,
    }
