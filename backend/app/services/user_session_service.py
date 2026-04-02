import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update as sa_update, case

from app.models.user_session import UserSession
from app.models.user import User
from app.models.ticket import Ticket
from app.core.rbac import UserRole
from app.services.geo_service import resolve_city

STALE_TIMEOUT = timedelta(minutes=5)


async def start_session(
    db: AsyncSession,
    user_id: uuid.UUID,
    session_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> UserSession:
    """Create a new session row. City is resolved async from IP."""
    city = await resolve_city(ip_address)
    now = datetime.now(timezone.utc)
    session = UserSession(
        user_id=user_id,
        session_id=session_id,
        started_at=now,
        last_heartbeat=now,
        ip_address=ip_address,
        city=city,
        user_agent=user_agent[:255] if user_agent and len(user_agent) > 255 else user_agent,
    )
    db.add(session)
    return session


async def end_session(
    db: AsyncSession,
    session_id: str,
    reason: str,
) -> None:
    """Close an active session by session_id."""
    now = datetime.now(timezone.utc)
    await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.session_id == session_id,
            UserSession.ended_at.is_(None),
        )
        .values(ended_at=now, end_reason=reason)
    )


async def update_heartbeat(db: AsyncSession, session_id: str) -> None:
    """Update last_heartbeat for the active session."""
    now = datetime.now(timezone.utc)
    await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.session_id == session_id,
            UserSession.ended_at.is_(None),
        )
        .values(last_heartbeat=now)
    )


async def close_stale_sessions(db: AsyncSession) -> int:
    """Close sessions with no heartbeat for >5 minutes. Returns count closed."""
    cutoff = datetime.now(timezone.utc) - STALE_TIMEOUT
    result = await db.execute(
        sa_update(UserSession)
        .where(
            UserSession.ended_at.is_(None),
            UserSession.last_heartbeat < cutoff,
        )
        .values(ended_at=UserSession.last_heartbeat, end_reason="timeout")
    )
    await db.commit()
    return result.rowcount


def _ticket_count_subquery(user_id_col, started_at_col, ended_at_col, role_col):
    """Build a correlated subquery for ticket counts based on role."""
    # For BILLING_OPERATOR: tickets created during session
    billing_count = (
        select(func.count())
        .where(
            Ticket.created_by == user_id_col,
            Ticket.created_at >= started_at_col,
            Ticket.created_at <= func.coalesce(ended_at_col, func.now()),
        )
        .correlate(UserSession)
        .scalar_subquery()
    )
    # For TICKET_CHECKER: tickets verified during session
    checker_count = (
        select(func.count())
        .where(
            Ticket.status == "VERIFIED",
            Ticket.updated_by == user_id_col,
            Ticket.checked_in_at >= started_at_col,
            Ticket.checked_in_at <= func.coalesce(ended_at_col, func.now()),
        )
        .correlate(UserSession)
        .scalar_subquery()
    )
    return case(
        (role_col == UserRole.BILLING_OPERATOR.value, billing_count),
        (role_col == UserRole.TICKET_CHECKER.value, checker_count),
        else_=None,
    )


async def get_active_sessions(db: AsyncSession) -> list[dict]:
    """Return all active sessions with user info and ticket counts."""
    ticket_count = _ticket_count_subquery(
        User.id, UserSession.started_at, UserSession.ended_at, User.role
    )
    query = (
        select(
            UserSession.id,
            UserSession.user_id,
            UserSession.session_id,
            UserSession.started_at,
            UserSession.last_heartbeat,
            UserSession.ip_address,
            UserSession.city,
            UserSession.user_agent,
            User.full_name,
            User.username,
            User.role,
            ticket_count.label("ticket_count"),
        )
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.ended_at.is_(None))
        .order_by(UserSession.started_at.desc())
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": row.id,
            "user_id": str(row.user_id),
            "session_id": row.session_id,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "last_heartbeat": row.last_heartbeat.isoformat() if row.last_heartbeat else None,
            "ip_address": row.ip_address,
            "city": row.city,
            "user_agent": row.user_agent,
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
            "ticket_count": row.ticket_count,
        }
        for row in rows
    ]


async def get_session_history(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id_filter: uuid.UUID | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[dict]:
    """Return paginated session history with user info and ticket counts."""
    ticket_count = _ticket_count_subquery(
        User.id, UserSession.started_at, UserSession.ended_at, User.role
    )
    query = (
        select(
            UserSession.id,
            UserSession.user_id,
            UserSession.session_id,
            UserSession.started_at,
            UserSession.ended_at,
            UserSession.last_heartbeat,
            UserSession.end_reason,
            UserSession.ip_address,
            UserSession.city,
            UserSession.user_agent,
            User.full_name,
            User.username,
            User.role,
            ticket_count.label("ticket_count"),
        )
        .join(User, User.id == UserSession.user_id)
    )
    if date_from:
        query = query.where(UserSession.started_at >= date_from)
    if date_to:
        query = query.where(UserSession.started_at <= date_to)
    if user_id_filter:
        query = query.where(UserSession.user_id == user_id_filter)

    query = query.order_by(UserSession.started_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    return [
        {
            "id": row.id,
            "user_id": str(row.user_id),
            "session_id": row.session_id,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "ended_at": row.ended_at.isoformat() if row.ended_at else None,
            "last_heartbeat": row.last_heartbeat.isoformat() if row.last_heartbeat else None,
            "end_reason": row.end_reason,
            "ip_address": row.ip_address,
            "city": row.city,
            "user_agent": row.user_agent,
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
            "ticket_count": row.ticket_count,
        }
        for row in rows
    ]


async def count_session_history(
    db: AsyncSession,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    user_id_filter: uuid.UUID | None = None,
) -> int:
    """Count total sessions matching filters (for pagination)."""
    query = select(func.count()).select_from(UserSession)
    if date_from:
        query = query.where(UserSession.started_at >= date_from)
    if date_to:
        query = query.where(UserSession.started_at <= date_to)
    if user_id_filter:
        query = query.where(UserSession.user_id == user_id_filter)
    result = await db.execute(query)
    return result.scalar() or 0
