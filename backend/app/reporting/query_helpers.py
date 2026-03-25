"""
Canonical query filter helpers for POS and Portal data sources.

Rules enforced here (and only here):
  POS   — Ticket.is_cancelled == False,  date axis = ticket_date
  Portal — Booking.status == 'CONFIRMED', date axis = travel_date
            NEVER Booking.is_cancelled

All report functions must use these helpers instead of inlining WHERE clauses.
"""
from __future__ import annotations

from app.models.booking import Booking
from app.models.ticket import Ticket
from app.reporting.filters import ReportFilters


def apply_pos_filters(query, filters: ReportFilters):
    """
    Apply standard POS WHERE clauses to a SQLAlchemy query that selects from
    the ``tickets`` table.

    Always applied
    --------------
    * ``Ticket.is_cancelled == False``
    * ``Ticket.ticket_date BETWEEN date_from AND date_to``

    Applied when the field is set in *filters*
    ------------------------------------------
    * ``Ticket.branch_id``
    * ``Ticket.route_id``
    * ``Ticket.payment_mode_id``

    Parameters
    ----------
    query   : A SQLAlchemy select() statement already referencing ``Ticket``.
    filters : ReportFilters instance.

    Returns
    -------
    The modified query.
    """
    query = query.where(Ticket.is_cancelled == False)  # noqa: E712
    query = query.where(Ticket.ticket_date >= filters.date_from)
    query = query.where(Ticket.ticket_date <= filters.date_to)
    if filters.branch_id is not None:
        query = query.where(Ticket.branch_id == filters.branch_id)
    if filters.route_id is not None:
        query = query.where(Ticket.route_id == filters.route_id)
    if filters.payment_mode_id is not None:
        query = query.where(Ticket.payment_mode_id == filters.payment_mode_id)
    return query


def apply_portal_filters(query, filters: ReportFilters):
    """
    Apply standard Portal WHERE clauses to a SQLAlchemy query that selects
    from the ``bookings`` table.

    Always applied
    --------------
    * ``Booking.status == 'CONFIRMED'``       ← authoritative active guard
    * ``Booking.travel_date BETWEEN date_from AND date_to``

    NEVER applied
    -------------
    * ``Booking.is_cancelled`` — use ``status == 'CONFIRMED'`` instead.
      A booking may have ``is_cancelled=False`` and still be PENDING (unpaid).

    Applied when the field is set in *filters*
    ------------------------------------------
    * ``Booking.branch_id``
    * ``Booking.route_id``
    * ``Booking.payment_mode_id``

    Parameters
    ----------
    query   : A SQLAlchemy select() statement already referencing ``Booking``.
    filters : ReportFilters instance.

    Returns
    -------
    The modified query.
    """
    query = query.where(Booking.status == "CONFIRMED")
    query = query.where(Booking.travel_date >= filters.date_from)
    query = query.where(Booking.travel_date <= filters.date_to)
    if filters.branch_id is not None:
        query = query.where(Booking.branch_id == filters.branch_id)
    if filters.route_id is not None:
        query = query.where(Booking.route_id == filters.route_id)
    if filters.payment_mode_id is not None:
        query = query.where(Booking.payment_mode_id == filters.payment_mode_id)
    return query


def apply_role_scope(query, user_context: dict | None = None):
    """
    Hook for future role-based query restrictions.

    Stub — currently returns the query unchanged.

    Future implementation will restrict rows based on:
    * ``user_context["allowed_branch_ids"]`` — list of branch IDs the user may see
    * ``user_context["allowed_route_ids"]``  — list of route IDs the user may see
    * ``user_context["user_role"]``          — role string for additional logic

    Parameters
    ----------
    query        : Any SQLAlchemy select() statement.
    user_context : Dict with role metadata, or None for unrestricted access.

    Returns
    -------
    The (currently unmodified) query.
    """
    # TODO: enforce role-based scope when RBAC reporting restrictions are added
    return query
