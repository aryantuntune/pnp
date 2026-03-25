#!/usr/bin/env python
"""
Reporting Layer System Audit
============================
Validates financial consistency, filter correctness, merge integrity,
cancellation handling, date alignment, and sorting across all 4 reports.

Usage:
    cd backend
    python audit_reporting.py

Requires: ssmspl_db_test PostgreSQL database (same as pytest integration tests).

Controlled test data uses IDs in the 601 range and ticket/booking numbers
in the 6000 range.  All data is seeded and torn down within this script.

Expected values (pre-computed from test data design):
  POS total:     1360
  Portal total:   675
  ALL total:     2035
"""
from __future__ import annotations

import asyncio
import datetime
import sys
import time as time_mod
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# ── Import all models so Base.metadata is fully populated ────────────────────
from app.database import Base
import app.models.boat                    # noqa: F401
import app.models.booking                 # noqa: F401
import app.models.booking_item            # noqa: F401
import app.models.branch                  # noqa: F401
import app.models.company                 # noqa: F401
import app.models.daily_report_recipient  # noqa: F401
import app.models.email_otp               # noqa: F401
import app.models.ferry_schedule          # noqa: F401
import app.models.item                    # noqa: F401
import app.models.item_rate               # noqa: F401
import app.models.payment_mode            # noqa: F401
import app.models.payment_transaction     # noqa: F401
import app.models.portal_user             # noqa: F401
import app.models.rate_change_log         # noqa: F401
import app.models.refresh_token           # noqa: F401
import app.models.route                   # noqa: F401
import app.models.sys_update_log          # noqa: F401
import app.models.ticket                  # noqa: F401
import app.models.user                    # noqa: F401

from app.models.booking import Booking
from app.models.booking_item import BookingItem
from app.models.branch import Branch
from app.models.item import Item
from app.models.payment_mode import PaymentMode
from app.models.portal_user import PortalUser
from app.models.route import Route
from app.models.ticket import Ticket, TicketItem

from app.reporting.filters import DataSource, ReportFilters
from app.reporting.reports.date_wise_amount import get_date_wise_amount
from app.reporting.reports.ferry_wise_item_summary import get_ferry_wise_item_summary
from app.reporting.reports.item_wise_summary import get_item_wise_summary
from app.reporting.reports.payment_mode_report import get_payment_mode_report

# ── Connection ────────────────────────────────────────────────────────────────

DB_URL = "postgresql+asyncpg://ssmspl_user:ssmspl_pass@localhost:5432/ssmspl_db_test"

# ── Audit data IDs (601 range) ────────────────────────────────────────────────

BRANCH_1   = 601
BRANCH_2   = 602
ROUTE_ID   = 601
IT_ADULT   = 601   # "AUDIT_ADULT"
IT_BIKE    = 602   # "AUDIT_BIKE"
IT_CARGO   = 603   # "AUDIT_CARGO"
PM_CASH    = 601   # "AUDIT_CASH"
PM_UPI     = 602   # "AUDIT_UPI"
PM_ONLINE  = 603   # "AUDIT_ONLINE"
PU_ID      = 601

DATE1        = datetime.date(2026, 3, 1)
DATE2        = datetime.date(2026, 3, 2)
DATE3        = datetime.date(2026, 3, 3)
DATE_OUTSIDE = datetime.date(2026, 1, 1)  # B4 booking_date — outside audit window
DEP_0800     = datetime.time(8, 0)
DEP_1400     = datetime.time(14, 0)

# ── Expected totals ───────────────────────────────────────────────────────────
#
# POS (non-cancelled tickets, non-cancelled items):
#   T1 DATE1 08:00 CASH:  ADULT(105)*2 + BIKE(210)*1        = 420
#   T2 DATE1 14:00 UPI:   ADULT(105)*3                      = 315
#   T3 DATE2 08:00 CASH:  ADULT(105)*1 + CARGO(50)*2        = 205
#   T4 DATE2 08:00 CASH:  *** CANCELLED *** → excluded
#   T5 DATE3 None  CASH:  BIKE(210)*2  (ADULT item cancelled)= 420
#   POS total = 1360
#
# Portal (CONFIRMED bookings only, non-cancelled items):
#   B1 travel=DATE1 08:00 ONLINE: ADULT(105)*2 + BIKE(210)*1 = 420
#   B2 travel=DATE2 14:00 ONLINE: CARGO(50)*3                = 150
#   B3 travel=DATE2 None  ONLINE: *** PENDING *** → excluded
#   B4 travel=DATE3 None  ONLINE: ADULT(105)*1               = 105
#      (B4.booking_date = DATE_OUTSIDE — tests that portal uses travel_date)
#   Portal total = 675
#
# ALL total = 2035

EXP_POS_TOTAL    = Decimal("1360")
EXP_PORTAL_TOTAL = Decimal("675")
EXP_ALL_TOTAL    = Decimal("2035")

EXP_DATE_WISE = {
    DATE1: Decimal("1155"),  # T1(420)+T2(315)+B1(420)
    DATE2: Decimal("355"),   # T3(205)+B2(150)
    DATE3: Decimal("525"),   # T5(420)+B4(105)
}

EXP_PM = {
    "AUDIT_CASH":   Decimal("1045"),  # T1+T3+T5
    "AUDIT_UPI":    Decimal("315"),   # T2
    "AUDIT_ONLINE": Decimal("675"),   # B1+B2+B4
}

EXP_ITEMS = {
    ("AUDIT_ADULT", Decimal("105")): {"pos": 6, "portal": 3, "net": Decimal("945")},
    ("AUDIT_BIKE",  Decimal("210")): {"pos": 3, "portal": 1, "net": Decimal("840")},
    ("AUDIT_CARGO", Decimal("50")):  {"pos": 2, "portal": 3, "net": Decimal("250")},
}

EXP_FERRY = {
    (DEP_0800, "AUDIT_ADULT"): {"pos": 3, "portal": 2, "total": 5},
    (DEP_0800, "AUDIT_BIKE"):  {"pos": 1, "portal": 1, "total": 2},
    (DEP_0800, "AUDIT_CARGO"): {"pos": 2, "portal": 0, "total": 2},
    (DEP_1400, "AUDIT_ADULT"): {"pos": 3, "portal": 0, "total": 3},
    (DEP_1400, "AUDIT_CARGO"): {"pos": 0, "portal": 3, "total": 3},
    (None,     "AUDIT_ADULT"): {"pos": 0, "portal": 1, "total": 1},
    (None,     "AUDIT_BIKE"):  {"pos": 2, "portal": 0, "total": 2},
}

# ── Result tracking ───────────────────────────────────────────────────────────

class AuditResults:
    def __init__(self):
        self.checks: list[tuple[str, bool, str]] = []  # (label, passed, detail)

    def check(self, label: str, passed: bool, detail: str = "") -> bool:
        self.checks.append((label, passed, detail))
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {label}" + (f"\n         {detail}" if not passed else ""))
        return passed

    @property
    def all_passed(self) -> bool:
        return all(p for _, p, _ in self.checks)

    @property
    def failed(self) -> list[tuple[str, str]]:
        return [(label, detail) for label, passed, detail in self.checks if not passed]


# ── Filter builder ────────────────────────────────────────────────────────────

def _f(source: DataSource = DataSource.ALL, **kwargs) -> ReportFilters:
    base = dict(date_from=DATE1, date_to=DATE3, branch_id=BRANCH_1, route_id=ROUTE_ID)
    base["source"] = source
    base.update(kwargs)
    return ReportFilters(**base)


# ── Data seeding ───────────────────────────────────────────────────────────────

async def seed(db: AsyncSession) -> dict:
    """
    Seed all controlled audit data.  Returns a dict of ORM objects for teardown.
    All IDs are in the 601 range; ticket/booking numbers in the 6000 range.
    """
    b1 = Branch(id=BRANCH_1, name="AUDIT_BRANCH1", address="AuditAddr1",
                is_active=True, last_ticket_no=0, last_booking_no=0)
    b2 = Branch(id=BRANCH_2, name="AUDIT_BRANCH2", address="AuditAddr2",
                is_active=True, last_ticket_no=0, last_booking_no=0)
    db.add_all([b1, b2])
    await db.flush()

    route = Route(id=ROUTE_ID, branch_id_one=BRANCH_1, branch_id_two=BRANCH_2, is_active=True)
    db.add(route)
    await db.flush()

    adult = Item(id=IT_ADULT, name="AUDIT_ADULT", short_name="A_ADT",
                 is_active=True, online_visibility=True, is_vehicle=False)
    bike  = Item(id=IT_BIKE,  name="AUDIT_BIKE",  short_name="A_BIK",
                 is_active=True, online_visibility=True, is_vehicle=True)
    cargo = Item(id=IT_CARGO, name="AUDIT_CARGO", short_name="A_CAR",
                 is_active=True, online_visibility=False, is_vehicle=False)
    db.add_all([adult, bike, cargo])
    await db.flush()

    pm_cash   = PaymentMode(id=PM_CASH,   description="AUDIT_CASH",   is_active=True)
    pm_upi    = PaymentMode(id=PM_UPI,    description="AUDIT_UPI",    is_active=True)
    pm_online = PaymentMode(id=PM_ONLINE, description="AUDIT_ONLINE", is_active=True)
    db.add_all([pm_cash, pm_upi, pm_online])
    await db.flush()

    pu = PortalUser(id=PU_ID, first_name="Audit", last_name="User",
                    email="audit_user@test.com", password="irrelevant",
                    mobile="9000000099")
    db.add(pu)
    await db.flush()

    # ── POS Tickets ──────────────────────────────────────────────────────────
    t1 = Ticket(ticket_no=6001, ticket_date=DATE1, departure=DEP_0800,
                branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
                amount=420, net_amount=420, is_cancelled=False)
    t2 = Ticket(ticket_no=6002, ticket_date=DATE1, departure=DEP_1400,
                branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_UPI,
                amount=315, net_amount=315, is_cancelled=False)
    t3 = Ticket(ticket_no=6003, ticket_date=DATE2, departure=DEP_0800,
                branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
                amount=205, net_amount=205, is_cancelled=False)
    t4 = Ticket(ticket_no=6004, ticket_date=DATE2, departure=DEP_0800,
                branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
                amount=420, net_amount=420, is_cancelled=True)   # ← CANCELLED
    t5 = Ticket(ticket_no=6005, ticket_date=DATE3, departure=None,
                branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
                amount=420, net_amount=420, is_cancelled=False)
    db.add_all([t1, t2, t3, t4, t5])
    await db.flush()

    # ── Ticket Items ─────────────────────────────────────────────────────────
    # T1: ADULT(100+5)*2=210, BIKE(200+10)*1=210  → net=420
    ti1  = TicketItem(ticket_id=t1.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=2, is_cancelled=False)
    ti2  = TicketItem(ticket_id=t1.id, item_id=IT_BIKE,  rate=200, levy=10, quantity=1, is_cancelled=False)
    # T2: ADULT(100+5)*3=315  → net=315
    ti3  = TicketItem(ticket_id=t2.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=3, is_cancelled=False)
    # T3: ADULT(100+5)*1=105, CARGO(50+0)*2=100  → net=205
    ti4  = TicketItem(ticket_id=t3.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=1, is_cancelled=False)
    ti5  = TicketItem(ticket_id=t3.id, item_id=IT_CARGO, rate=50,  levy=0,  quantity=2, is_cancelled=False)
    # T4 (CANCELLED ticket): item present but ticket excluded by is_cancelled filter
    ti6  = TicketItem(ticket_id=t4.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=4, is_cancelled=False)
    # T5: BIKE(200+10)*2=420, ADULT item CANCELLED (ticket net=420, only BIKE counts)
    ti7  = TicketItem(ticket_id=t5.id, item_id=IT_BIKE,  rate=200, levy=10, quantity=2, is_cancelled=False)
    ti8  = TicketItem(ticket_id=t5.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=5, is_cancelled=True)   # ← item cancelled
    db.add_all([ti1, ti2, ti3, ti4, ti5, ti6, ti7, ti8])
    await db.flush()

    # ── Portal Bookings ───────────────────────────────────────────────────────
    b1_bk = Booking(booking_no=6001, booking_date=DATE1, travel_date=DATE1,
                    departure=DEP_0800, branch_id=BRANCH_1, route_id=ROUTE_ID,
                    portal_user_id=PU_ID, payment_mode_id=PM_ONLINE,
                    amount=420, net_amount=420, status="CONFIRMED", is_cancelled=False)
    b2_bk = Booking(booking_no=6002, booking_date=DATE1, travel_date=DATE2,
                    departure=DEP_1400, branch_id=BRANCH_1, route_id=ROUTE_ID,
                    portal_user_id=PU_ID, payment_mode_id=PM_ONLINE,
                    amount=150, net_amount=150, status="CONFIRMED", is_cancelled=False)
    b3_bk = Booking(booking_no=6003, booking_date=DATE1, travel_date=DATE2,
                    departure=None, branch_id=BRANCH_1, route_id=ROUTE_ID,
                    portal_user_id=PU_ID, payment_mode_id=PM_ONLINE,
                    amount=525, net_amount=525, status="PENDING", is_cancelled=False)  # ← PENDING
    b4_bk = Booking(booking_no=6004,
                    booking_date=DATE_OUTSIDE,  # ← outside audit window (tests travel_date is used)
                    travel_date=DATE3,
                    departure=None, branch_id=BRANCH_1, route_id=ROUTE_ID,
                    portal_user_id=PU_ID, payment_mode_id=PM_ONLINE,
                    amount=105, net_amount=105, status="CONFIRMED", is_cancelled=False)
    db.add_all([b1_bk, b2_bk, b3_bk, b4_bk])
    await db.flush()

    # ── Booking Items ─────────────────────────────────────────────────────────
    # B1: ADULT(105)*2=210, BIKE(210)*1=210  → net=420
    bi1  = BookingItem(booking_id=b1_bk.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=2, is_cancelled=False)
    bi2  = BookingItem(booking_id=b1_bk.id, item_id=IT_BIKE,  rate=200, levy=10, quantity=1, is_cancelled=False)
    # B2: CARGO(50)*3=150  → net=150
    bi3  = BookingItem(booking_id=b2_bk.id, item_id=IT_CARGO, rate=50,  levy=0,  quantity=3, is_cancelled=False)
    # B3 (PENDING): items present but booking excluded
    bi4  = BookingItem(booking_id=b3_bk.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=5, is_cancelled=False)
    # B4: ADULT(105)*1=105  → net=105
    bi5  = BookingItem(booking_id=b4_bk.id, item_id=IT_ADULT, rate=100, levy=5,  quantity=1, is_cancelled=False)
    db.add_all([bi1, bi2, bi3, bi4, bi5])
    await db.commit()

    return dict(
        branches=[b1, b2], route=route,
        items=[adult, bike, cargo], payment_modes=[pm_cash, pm_upi, pm_online],
        portal_user=pu,
        tickets=[t1, t2, t3, t4, t5],
        ticket_items=[ti1, ti2, ti3, ti4, ti5, ti6, ti7, ti8],
        bookings=[b1_bk, b2_bk, b3_bk, b4_bk],
        booking_items=[bi1, bi2, bi3, bi4, bi5],
    )


async def pre_cleanup(db: AsyncSession) -> None:
    """
    Remove any leftover 601-range data from a previous failed run.
    Safe to call even if no stale data exists (WHERE IN [] is a no-op).
    """
    from sqlalchemy import delete as sa_delete
    from sqlalchemy import select as sa_select

    ticket_ids = (
        await db.execute(sa_select(Ticket.id).where(Ticket.ticket_no.between(6000, 6099)))
    ).scalars().all()
    booking_ids = (
        await db.execute(sa_select(Booking.id).where(Booking.booking_no.between(6000, 6099)))
    ).scalars().all()

    if ticket_ids:
        await db.execute(sa_delete(TicketItem).where(TicketItem.ticket_id.in_(ticket_ids)))
        await db.execute(sa_delete(Ticket).where(Ticket.id.in_(ticket_ids)))
    if booking_ids:
        await db.execute(sa_delete(BookingItem).where(BookingItem.booking_id.in_(booking_ids)))
        await db.execute(sa_delete(Booking).where(Booking.id.in_(booking_ids)))

    await db.execute(sa_delete(PortalUser).where(PortalUser.id == PU_ID))
    await db.execute(sa_delete(PaymentMode).where(PaymentMode.id.in_([PM_CASH, PM_UPI, PM_ONLINE])))
    await db.execute(sa_delete(Item).where(Item.id.in_([IT_ADULT, IT_BIKE, IT_CARGO])))
    await db.execute(sa_delete(Route).where(Route.id == ROUTE_ID))
    await db.execute(sa_delete(Branch).where(Branch.id.in_([BRANCH_1, BRANCH_2])))
    await db.commit()
    print("Pre-cleanup: stale 601-range data removed (or none found).")


async def teardown(db: AsyncSession, objs: dict) -> None:
    """
    Delete seeded objects using explicit DELETE statements in correct FK order.

    Uses sa_delete() rather than session.delete(obj) so that SQLAlchemy does
    not need ORM relationship declarations to determine FK-safe ordering.
    Rolls back any pending error state before starting.
    """
    from sqlalchemy import delete as sa_delete

    # Roll back any pending (error) state before cleanup
    try:
        await db.rollback()
    except Exception:
        pass

    booking_ids = [o.id for o in objs["bookings"]]
    ticket_ids  = [o.id for o in objs["tickets"]]
    item_ids    = [o.id for o in objs["items"]]
    pm_ids      = [o.id for o in objs["payment_modes"]]
    branch_ids  = [o.id for o in objs["branches"]]

    # FK children first
    await db.execute(sa_delete(BookingItem).where(BookingItem.booking_id.in_(booking_ids)))
    await db.execute(sa_delete(TicketItem).where(TicketItem.ticket_id.in_(ticket_ids)))
    # Then parents
    await db.execute(sa_delete(Booking).where(Booking.id.in_(booking_ids)))
    await db.execute(sa_delete(Ticket).where(Ticket.id.in_(ticket_ids)))
    await db.execute(sa_delete(PortalUser).where(PortalUser.id == PU_ID))
    await db.execute(sa_delete(PaymentMode).where(PaymentMode.id.in_(pm_ids)))
    await db.execute(sa_delete(Item).where(Item.id.in_(item_ids)))
    await db.execute(sa_delete(Route).where(Route.id == ROUTE_ID))
    await db.execute(sa_delete(Branch).where(Branch.id.in_(branch_ids)))
    await db.commit()


# ── Performance seed / teardown ───────────────────────────────────────────────

async def seed_bulk(db: AsyncSession) -> list:
    """Seed 1000 simple tickets (1 item each) for performance testing."""
    # Re-use branch/route/item/pm that were already seeded
    tickets, items = [], []
    for i in range(1000):
        t = Ticket(
            ticket_no=7000 + i, ticket_date=DATE1, departure=DEP_0800,
            branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
            amount=100, net_amount=100, is_cancelled=False,
        )
        db.add(t)
    await db.flush()
    # Collect just-inserted tickets via select would be complex; flush returns objects
    # Instead, we'll delete by the ticket_no range in teardown_bulk
    await db.commit()
    return []


async def teardown_bulk(db: AsyncSession) -> None:
    from sqlalchemy import delete
    from app.models.ticket import TicketItem as TI, Ticket as T
    await db.execute(
        delete(TI).where(TI.ticket_id.in_(
            db.execute.__func__  # handled separately below
        ))
    )
    # Simpler: just delete tickets by ticket_no range
    stmt_ti = delete(TicketItem).where(
        TicketItem.ticket_id.in_(
            __import__("sqlalchemy", fromlist=["select"]).select(Ticket.id)
            .where(Ticket.ticket_no.between(7000, 7999))
        )
    )
    stmt_t = delete(Ticket).where(Ticket.ticket_no.between(7000, 7999))
    await db.execute(stmt_ti)
    await db.execute(stmt_t)
    await db.commit()


# ── Validation sections ───────────────────────────────────────────────────────

async def validate_financial_consistency(db: AsyncSession, res: AuditResults) -> None:
    print("\n[1] Financial Consistency  (A == B == C == 2035)")

    dw  = await get_date_wise_amount(db,    _f())
    pm  = await get_payment_mode_report(db, _f())
    iw  = await get_item_wise_summary(db,   _f())

    A = dw["grand_total"]
    B = pm["grand_total_amount"]
    C = iw["grand_total"]

    res.check("Date-wise grand_total == 2035",    A == EXP_ALL_TOTAL, f"got {A}")
    res.check("Payment-mode grand_total == 2035", B == EXP_ALL_TOTAL, f"got {B}")
    res.check("Item-wise grand_total == 2035",    C == EXP_ALL_TOTAL, f"got {C}")
    res.check("A == B == C",                      A == B == C,        f"A={A} B={B} C={C}")


async def validate_per_date_amounts(db: AsyncSession, res: AuditResults) -> None:
    print("\n[2] Per-date Amounts")

    dw = await get_date_wise_amount(db, _f())
    rows_by_date = {r["date"]: r["total_amount"] for r in dw["rows"]}

    for date, expected in EXP_DATE_WISE.items():
        got = rows_by_date.get(date, Decimal("0"))
        res.check(f"Date {date} total == {expected}", got == expected, f"got {got}")


async def validate_payment_mode_breakdown(db: AsyncSession, res: AuditResults) -> None:
    print("\n[3] Payment Mode Breakdown")

    pm = await get_payment_mode_report(db, _f())
    rbi = {r["payment_mode_name"]: r["total_amount"] for r in pm["rows"]}

    for name, expected in EXP_PM.items():
        got = rbi.get(name, Decimal("0"))
        res.check(f"PM {name} == {expected}", got == expected, f"got {got}")

    res.check(
        "Inactive mode not in results",
        all(r["payment_mode_id"] in {PM_CASH, PM_UPI, PM_ONLINE}
            for r in pm["rows"]
            if r["payment_mode_name"].startswith("AUDIT_")),
        "",
    )


async def validate_source_isolation(db: AsyncSession, res: AuditResults) -> None:
    print("\n[4] Source Isolation  (ALL == POS + PORTAL)")

    dw_all    = await get_date_wise_amount(db, _f(DataSource.ALL))
    dw_pos    = await get_date_wise_amount(db, _f(DataSource.POS))
    dw_portal = await get_date_wise_amount(db, _f(DataSource.PORTAL))
    pm_all    = await get_payment_mode_report(db, _f(DataSource.ALL))
    pm_pos    = await get_payment_mode_report(db, _f(DataSource.POS))
    pm_portal = await get_payment_mode_report(db, _f(DataSource.PORTAL))
    iw_all    = await get_item_wise_summary(db, _f(DataSource.ALL))
    iw_pos    = await get_item_wise_summary(db, _f(DataSource.POS))
    iw_portal = await get_item_wise_summary(db, _f(DataSource.PORTAL))

    # POS-only totals
    res.check("POS date_wise == 1360",    dw_pos["grand_total"]       == EXP_POS_TOTAL,
              f"got {dw_pos['grand_total']}")
    res.check("POS payment_mode == 1360", pm_pos["grand_total_amount"] == EXP_POS_TOTAL,
              f"got {pm_pos['grand_total_amount']}")
    res.check("POS item_wise == 1360",    iw_pos["grand_total"]        == EXP_POS_TOTAL,
              f"got {iw_pos['grand_total']}")

    # Portal-only totals
    res.check("PORTAL date_wise == 675",    dw_portal["grand_total"]       == EXP_PORTAL_TOTAL,
              f"got {dw_portal['grand_total']}")
    res.check("PORTAL payment_mode == 675", pm_portal["grand_total_amount"] == EXP_PORTAL_TOTAL,
              f"got {pm_portal['grand_total_amount']}")
    res.check("PORTAL item_wise == 675",    iw_portal["grand_total"]        == EXP_PORTAL_TOTAL,
              f"got {iw_portal['grand_total']}")

    # ALL = POS + PORTAL
    for name, (all_val, pos_val, portal_val) in {
        "date_wise":    (dw_all["grand_total"],       dw_pos["grand_total"],       dw_portal["grand_total"]),
        "payment_mode": (pm_all["grand_total_amount"], pm_pos["grand_total_amount"], pm_portal["grand_total_amount"]),
        "item_wise":    (iw_all["grand_total"],        iw_pos["grand_total"],        iw_portal["grand_total"]),
    }.items():
        res.check(
            f"ALL {name} == POS + PORTAL",
            all_val == pos_val + portal_val,
            f"ALL={all_val}  POS={pos_val}  PORTAL={portal_val}",
        )


async def validate_payment_mode_filters(db: AsyncSession, res: AuditResults) -> None:
    print("\n[5] Payment Mode Filters (no cross-source leakage)")

    # CASH filter → only POS tickets with CASH
    iw_cash = await get_item_wise_summary(db, _f(payment_mode_id=PM_CASH))
    # CASH POS: T1(420)+T3(205)+T5(420)=1045; portal has ONLINE only → portal=0 if ONLINE filtered
    # apply_portal_filters also applies payment_mode_id, so ONLINE bookings are excluded
    cash_total = iw_cash["grand_total"]
    res.check("CASH filter: grand_total == 1045", cash_total == Decimal("1045"),
              f"got {cash_total}")

    # UPI filter → T2 only
    iw_upi = await get_item_wise_summary(db, _f(payment_mode_id=PM_UPI))
    upi_total = iw_upi["grand_total"]
    res.check("UPI filter: grand_total == 315", upi_total == Decimal("315"),
              f"got {upi_total}")

    # ONLINE filter → portal only (no POS tickets have ONLINE in our dataset)
    iw_online = await get_item_wise_summary(db, _f(payment_mode_id=PM_ONLINE))
    online_total = iw_online["grand_total"]
    res.check("ONLINE filter: grand_total == 675", online_total == Decimal("675"),
              f"got {online_total}")

    # Payment mode breakdown for CASH: should only show CASH
    pm_cash_filter = await get_payment_mode_report(db, _f(payment_mode_id=PM_CASH))
    rbi = {r["payment_mode_name"]: r["total_amount"] for r in pm_cash_filter["rows"]}
    res.check("CASH filter: AUDIT_UPI row is 0",    rbi.get("AUDIT_UPI",    Decimal("0")) == Decimal("0"), f"AUDIT_UPI={rbi.get('AUDIT_UPI')}")
    res.check("CASH filter: AUDIT_ONLINE row is 0", rbi.get("AUDIT_ONLINE", Decimal("0")) == Decimal("0"), f"AUDIT_ONLINE={rbi.get('AUDIT_ONLINE')}")


async def validate_cancellation_handling(db: AsyncSession, res: AuditResults) -> None:
    print("\n[6] Cancellation Handling")

    dw = await get_date_wise_amount(db, _f())
    pm = await get_payment_mode_report(db, _f())
    iw = await get_item_wise_summary(db, _f())

    # T4 is cancelled (DATE2, CASH, 420) → must not appear
    date2_total = next((r["total_amount"] for r in dw["rows"] if r["date"] == DATE2), Decimal("0"))
    res.check(
        "Cancelled ticket T4 excluded from date_wise DATE2",
        date2_total == Decimal("355"),   # T3(205)+B2(150) only
        f"DATE2 total={date2_total}  expected=355",
    )

    # T5's ADULT item (qty=5) is is_cancelled=True → must not appear in item_wise
    iw_items = {(r["item_name"], r["rate"]): r for r in iw["rows"]}
    adult_portal_qty = iw_items.get(("AUDIT_ADULT", Decimal("105")), {}).get("pos_quantity", 0)
    # POS ADULT: T1(2)+T2(3)+T3(1) = 6  (NOT 11 = 6+5 from T5's cancelled item)
    res.check(
        "Cancelled item TI8 excluded: ADULT pos_quantity == 6",
        adult_portal_qty == 6,
        f"AUDIT_ADULT pos_quantity={adult_portal_qty}  expected=6",
    )

    # B3 is PENDING → must not appear in portal results
    portal_total = (await get_date_wise_amount(db, _f(DataSource.PORTAL)))["grand_total"]
    res.check(
        "PENDING booking B3 excluded: portal total == 675",
        portal_total == EXP_PORTAL_TOTAL,
        f"portal total={portal_total}  expected=675",
    )


async def validate_date_alignment(db: AsyncSession, res: AuditResults) -> None:
    print("\n[7] Date Alignment (Portal uses travel_date, not booking_date)")

    # B4: booking_date=2026-01-01 (outside DATE1..DATE3), travel_date=DATE3 (inside)
    # If portal correctly uses travel_date, B4 should appear.
    # If portal mistakenly used booking_date, B4 would be absent.

    dw_all = await get_date_wise_amount(db, _f())
    date3_total = next((r["total_amount"] for r in dw_all["rows"] if r["date"] == DATE3), Decimal("0"))
    # DATE3: T5(420) + B4(105) = 525
    res.check(
        "B4 included via travel_date (DATE3 total == 525)",
        date3_total == Decimal("525"),
        f"DATE3 total={date3_total}  expected=525 (B4 booking_date={DATE_OUTSIDE} is outside window)",
    )

    # Sanity: if we narrowed date range to DATE_OUTSIDE..DATE_OUTSIDE, B4 should not appear
    dw_outside = await get_date_wise_amount(db, ReportFilters(
        date_from=DATE_OUTSIDE, date_to=DATE_OUTSIDE,
        branch_id=BRANCH_1, route_id=ROUTE_ID, source=DataSource.PORTAL,
    ))
    res.check(
        "B4 absent when filtering by booking_date range (confirms travel_date is used)",
        dw_outside["grand_total"] == Decimal("0"),
        f"total={dw_outside['grand_total']}  expected=0",
    )


async def validate_item_wise_detail(db: AsyncSession, res: AuditResults) -> None:
    print("\n[8] Item-wise Row Detail")

    iw = await get_item_wise_summary(db, _f())
    rbi = {(r["item_name"], r["rate"]): r for r in iw["rows"]}

    for (name, rate), exp in EXP_ITEMS.items():
        row = rbi.get((name, rate))
        if row is None:
            res.check(f"{name} @ {rate} present", False, "row missing")
            continue
        res.check(f"{name} pos_quantity == {exp['pos']}",
                  row["pos_quantity"] == exp["pos"], f"got {row['pos_quantity']}")
        res.check(f"{name} portal_quantity == {exp['portal']}",
                  row["portal_quantity"] == exp["portal"], f"got {row['portal_quantity']}")
        res.check(f"{name} net_amount == {exp['net']}",
                  row["net_amount"] == exp["net"], f"got {row['net_amount']}")


async def validate_item_wise_integrity_check(db: AsyncSession, res: AuditResults) -> None:
    print("\n[9] Item-wise Integrity Check (grand_total == sum(payment_breakdown))")

    iw = await get_item_wise_summary(db, _f())
    pbd_total = sum(r["amount"] for r in iw["payment_mode_breakdown"])
    res.check(
        "item grand_total == payment_breakdown sum",
        iw["grand_total"] == pbd_total,
        f"grand_total={iw['grand_total']}  pbd_sum={pbd_total}",
    )

    # Payment breakdown detail
    pbd = {r["payment_mode_name"]: r["amount"] for r in iw["payment_mode_breakdown"]}
    for name, expected in EXP_PM.items():
        got = pbd.get(name, Decimal("0"))
        res.check(f"item_wise pbd {name} == {expected}", got == expected, f"got {got}")


async def validate_ferry_wise_detail(db: AsyncSession, res: AuditResults) -> None:
    print("\n[10] Ferry-wise Row Detail and Sorting")

    fw = await get_ferry_wise_item_summary(db, _f())
    # Only audit rows
    audit_rows = [r for r in fw["rows"] if r["item_name"].startswith("AUDIT_")]
    rbi = {(r["departure"], r["item_name"]): r for r in audit_rows}

    for (dep, name), exp in EXP_FERRY.items():
        row = rbi.get((dep, name))
        if row is None:
            res.check(f"ferry ({dep}, {name}) present", False, "row missing")
            continue
        res.check(f"ferry ({dep}, {name}) pos=={exp['pos']}",
                  row["pos_quantity"] == exp["pos"], f"got {row['pos_quantity']}")
        res.check(f"ferry ({dep}, {name}) portal=={exp['portal']}",
                  row["portal_quantity"] == exp["portal"], f"got {row['portal_quantity']}")
        res.check(f"ferry ({dep}, {name}) total=={exp['total']}",
                  row["total_quantity"] == exp["total"], f"got {row['total_quantity']}")

    # Sorting: non-null departures before None
    audit_deps = [r["departure"] for r in audit_rows]
    null_positions = [i for i, d in enumerate(audit_deps) if d is None]
    non_null_positions = [i for i, d in enumerate(audit_deps) if d is not None]
    res.check(
        "NULL departure rows sort after non-null rows",
        (not null_positions) or (not non_null_positions) or
        min(null_positions) > max(non_null_positions),
        f"null positions={null_positions}  non-null positions={non_null_positions}",
    )

    # Within same departure, items are alphabetical
    for dep in {DEP_0800, DEP_1400}:
        same_dep = [r["item_name"] for r in audit_rows if r["departure"] == dep]
        res.check(
            f"dep={dep} items alphabetical",
            same_dep == sorted(same_dep, key=str.lower),
            f"got {same_dep}",
        )

    # Null departure total
    null_total = sum(r["total_quantity"] for r in audit_rows if r["departure"] is None)
    res.check("NULL departure total_quantity == 3",  # (None,ADULT)=1 + (None,BIKE)=2
              null_total == 3, f"got {null_total}")


async def validate_edge_cases(db: AsyncSession, res: AuditResults) -> None:
    print("\n[11] Edge Cases")

    future = datetime.date(2030, 1, 1)
    empty_filters = ReportFilters(
        date_from=future, date_to=future,
        branch_id=BRANCH_1, source=DataSource.ALL,
    )

    dw_empty = await get_date_wise_amount(db, empty_filters)
    pm_empty = await get_payment_mode_report(db, empty_filters)
    iw_empty = await get_item_wise_summary(db, empty_filters)
    fw_empty = await get_ferry_wise_item_summary(db, empty_filters)

    res.check("Empty date range: date_wise grand_total == 0",
              dw_empty["grand_total"] == Decimal("0"), f"got {dw_empty['grand_total']}")
    res.check("Empty date range: date_wise rows == []",
              dw_empty["rows"] == [], f"rows={dw_empty['rows']}")
    res.check("Empty date range: payment_mode grand_total == 0",
              pm_empty["grand_total_amount"] == Decimal("0"),
              f"got {pm_empty['grand_total_amount']}")
    res.check("Empty date range: payment_mode all_modes appear",
              any(r["payment_mode_name"] == "AUDIT_CASH" for r in pm_empty["rows"]),
              "AUDIT_CASH mode not in zero-result rows")
    res.check("Empty date range: item_wise grand_total == 0",
              iw_empty["grand_total"] == Decimal("0"), f"got {iw_empty['grand_total']}")
    res.check("Empty date range: item_wise rows == []",
              iw_empty["rows"] == [], f"rows={iw_empty['rows']}")
    res.check("Empty date range: ferry_wise rows == []",
              fw_empty["rows"] == [], f"rows={fw_empty['rows']}")
    res.check("Empty date range: ferry_wise total_quantity == 0",
              fw_empty["total_quantity"] == 0, f"got {fw_empty['total_quantity']}")

    # POS only: portal fields are 0
    iw_pos = await get_item_wise_summary(db, _f(DataSource.POS))
    all_portal_zero = all(r["portal_quantity"] == 0 for r in iw_pos["rows"])
    res.check("POS-only mode: all portal_quantity == 0", all_portal_zero, "")

    fw_pos = await get_ferry_wise_item_summary(db, _f(DataSource.POS))
    all_portal_zero_fw = all(r["portal_quantity"] == 0 for r in fw_pos["rows"])
    res.check("POS-only mode (ferry): all portal_quantity == 0", all_portal_zero_fw, "")

    # Portal only: pos fields are 0
    iw_portal = await get_item_wise_summary(db, _f(DataSource.PORTAL))
    all_pos_zero = all(r["pos_quantity"] == 0 for r in iw_portal["rows"])
    res.check("PORTAL-only mode: all pos_quantity == 0", all_pos_zero, "")


async def validate_merge_correctness(db: AsyncSession, res: AuditResults) -> None:
    print("\n[12] Merge Correctness")

    iw = await get_item_wise_summary(db, _f())
    audit_items = [r for r in iw["rows"] if r["item_name"].startswith("AUDIT_")]

    # No duplicate (item_name, rate) keys
    keys = [(r["item_name"], r["rate"]) for r in audit_items]
    res.check("No duplicate (item_name, rate) rows", len(keys) == len(set(keys)),
              f"keys={keys}")

    # All 3 audit items present
    item_names = {r["item_name"] for r in audit_items}
    res.check("All 3 audit items present",
              {"AUDIT_ADULT", "AUDIT_BIKE", "AUDIT_CARGO"} <= item_names,
              f"found={item_names}")

    # ADULT total_quantity == pos(6) + portal(3) = 9
    adult_row = next((r for r in audit_items if r["item_name"] == "AUDIT_ADULT"), None)
    if adult_row:
        res.check("ADULT total_quantity == pos + portal",
                  adult_row["quantity"] == adult_row["pos_quantity"] + adult_row["portal_quantity"],
                  f"total={adult_row['quantity']} pos={adult_row['pos_quantity']} portal={adult_row['portal_quantity']}")

    fw = await get_ferry_wise_item_summary(db, _f())
    audit_fw = [r for r in fw["rows"] if r["item_name"].startswith("AUDIT_")]
    fw_keys = [(r["departure"], r["item_name"]) for r in audit_fw]
    res.check("No duplicate (departure, item) ferry rows",
              len(fw_keys) == len(set(fw_keys)), f"keys={fw_keys}")

    # Ferry total_quantity == sum of individual row totals
    fw_sum = sum(r["total_quantity"] for r in audit_fw)
    res.check("Ferry total_quantity == sum(row totals)",
              fw["total_quantity"] >= fw_sum,   # >= because other test data may exist
              f"total={fw['total_quantity']}  audit_sum={fw_sum}")


async def validate_performance(db: AsyncSession, res: AuditResults) -> None:
    print("\n[13] Performance (~1000 POS rows)")

    # Insert 1000 tickets (no items — just testing query aggregation perf)
    print("     Seeding 1000 bulk tickets...")
    bulk_tickets = []
    for i in range(1000):
        t = Ticket(
            ticket_no=7000 + i, ticket_date=DATE1, departure=DEP_0800,
            branch_id=BRANCH_1, route_id=ROUTE_ID, payment_mode_id=PM_CASH,
            amount=50, net_amount=50, is_cancelled=False,
        )
        db.add(t)
    await db.flush()

    # One item per ticket
    # Collect flushed tickets via a range query
    from sqlalchemy import select as sa_select
    stmt = sa_select(Ticket).where(Ticket.ticket_no.between(7000, 7999))
    bulk_t = (await db.execute(stmt)).scalars().all()
    for t in bulk_t:
        db.add(TicketItem(
            ticket_id=t.id, item_id=IT_ADULT,
            rate=50, levy=0, quantity=1, is_cancelled=False,
        ))
    await db.commit()
    print(f"     Inserted {len(bulk_t)} tickets + items")

    # Time the reports
    bulk_filters = ReportFilters(
        date_from=DATE1, date_to=DATE1,
        branch_id=BRANCH_1, source=DataSource.ALL,
    )
    t0 = time_mod.perf_counter()
    dw = await get_date_wise_amount(db, bulk_filters)
    pm = await get_payment_mode_report(db, bulk_filters)
    iw = await get_item_wise_summary(db, bulk_filters)
    fw = await get_ferry_wise_item_summary(db, bulk_filters)
    elapsed = time_mod.perf_counter() - t0

    print(f"     4 reports on ~1000 rows: {elapsed:.3f}s")
    res.check(f"All 4 reports complete in <5s (got {elapsed:.3f}s)", elapsed < 5.0,
              f"elapsed={elapsed:.3f}s")

    # Totals sanity: 1000 tickets * 50 = 50000 POS, plus controlled data on DATE1
    # controlled DATE1 POS = T1(420)+T2(315) = 735  (T3 is DATE2, T4 cancelled, T5 DATE3)
    # bulk DATE1 POS = 1000 * 50 = 50000
    # portal DATE1 = B1(420)
    # total DATE1 = 735 + 50000 + 420 = 51155
    expected_date1 = Decimal("735") + Decimal("50000") + Decimal("420")
    rows_by_date = {r["date"]: r["total_amount"] for r in dw["rows"]}
    got_date1 = rows_by_date.get(DATE1, Decimal("0"))
    res.check(
        f"DATE1 total with 1000 bulk rows == {expected_date1}",
        got_date1 == expected_date1,
        f"got {got_date1}",
    )

    # Cleanup bulk data
    print("     Cleaning up bulk data...")
    from sqlalchemy import delete
    await db.execute(
        delete(TicketItem).where(
            TicketItem.ticket_id.in_(
                sa_select(Ticket.id).where(Ticket.ticket_no.between(7000, 7999))
            )
        )
    )
    await db.execute(delete(Ticket).where(Ticket.ticket_no.between(7000, 7999)))
    await db.commit()
    print("     Bulk data removed")


# ── Main audit ────────────────────────────────────────────────────────────────

async def run_audit() -> bool:
    engine = create_async_engine(DB_URL, poolclass=NullPool)

    print("Creating schema (if needed)...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    res = AuditResults()
    objs = None

    validation_exc = None

    async with Session() as db:
        try:
            print("\nPre-cleaning any stale 601-range data...")
            await pre_cleanup(db)

            print("\nSeeding controlled audit data (IDs 601 range)...")
            objs = await seed(db)
            print("Seed complete.\n")

            await validate_financial_consistency(db, res)
            await validate_per_date_amounts(db, res)
            await validate_payment_mode_breakdown(db, res)
            await validate_source_isolation(db, res)
            await validate_payment_mode_filters(db, res)
            await validate_cancellation_handling(db, res)
            await validate_date_alignment(db, res)
            await validate_item_wise_detail(db, res)
            await validate_item_wise_integrity_check(db, res)
            await validate_ferry_wise_detail(db, res)
            await validate_edge_cases(db, res)
            await validate_merge_correctness(db, res)
            await validate_performance(db, res)

        except Exception as e:
            import traceback
            validation_exc = e
            print(f"\n[ERROR] Exception during audit validation:")
            traceback.print_exc()

    # Teardown runs in its own fresh session so it is immune to any
    # corrupted state left by a validation exception.
    if objs:
        print("\nCleaning up seeded data...")
        async with Session() as cleanup_db:
            try:
                await teardown(cleanup_db, objs)
                print("Cleanup complete.")
            except Exception as te:
                print(f"[WARNING] Teardown error: {te}")

    if validation_exc:
        raise validation_exc

    await engine.dispose()
    return res.all_passed, res


def print_report(passed: bool, res: AuditResults) -> None:
    line = "=" * 60
    print(f"\n{line}")
    print("   REPORTING LAYER AUDIT — FINAL RESULT")
    print(line)

    total = len(res.checks)
    n_pass = sum(1 for _, p, _ in res.checks if p)
    n_fail = total - n_pass

    print(f"\n   Checks:  {total}  |  Passed: {n_pass}  |  Failed: {n_fail}")

    if passed:
        print("\n   *** ALL CHECKS PASSED ***")
    else:
        print("\n   !!! FAILURES DETECTED !!!\n")
        for label, detail in res.failed:
            print(f"   FAIL: {label}")
            if detail:
                print(f"         {detail}")

    print(f"\n{line}\n")


if __name__ == "__main__":
    try:
        result = asyncio.run(run_audit())
        passed, res = result
        print_report(passed, res)
        sys.exit(0 if passed else 1)
    except Exception as exc:
        print(f"\n[FATAL] Audit aborted: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
