import datetime as _dt
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.dependencies import require_roles
from app.core.rbac import UserRole
from app.models.user import User
from app.schemas.user_session import ActiveSessionRead, SessionHistoryRead, ActivitySummary
from app.services import user_session_service

router = APIRouter(prefix="/api/user-sessions", tags=["User Sessions"])

_super_admin_only = require_roles(UserRole.SUPER_ADMIN)


@router.get(
    "/active",
    response_model=list[ActiveSessionRead],
    summary="List active user sessions",
    description="Returns all currently active sessions with user info and ticket counts. SUPER_ADMIN only.",
)
async def list_active_sessions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    await user_session_service.close_stale_sessions(db)
    return await user_session_service.get_active_sessions(db)


@router.get(
    "/history",
    response_model=list[SessionHistoryRead],
    summary="List session history",
    description="Paginated session history with optional date and user filters. SUPER_ADMIN only.",
)
async def list_session_history(
    date_from: _dt.date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: _dt.date | None = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user UUID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    parsed_from = _dt.datetime.combine(date_from, _dt.time.min, tzinfo=_dt.timezone.utc) if date_from else None
    parsed_to = _dt.datetime.combine(date_to, _dt.time(23, 59, 59), tzinfo=_dt.timezone.utc) if date_to else None
    return await user_session_service.get_session_history(
        db, parsed_from, parsed_to, user_id, skip, limit,
    )


@router.get(
    "/history/count",
    response_model=int,
    summary="Count session history records",
    description="Total count for pagination. SUPER_ADMIN only.",
)
async def count_session_history(
    date_from: _dt.date | None = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: _dt.date | None = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: uuid.UUID | None = Query(None, description="Filter by user UUID"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    parsed_from = _dt.datetime.combine(date_from, _dt.time.min, tzinfo=_dt.timezone.utc) if date_from else None
    parsed_to = _dt.datetime.combine(date_to, _dt.time(23, 59, 59), tzinfo=_dt.timezone.utc) if date_to else None
    return await user_session_service.count_session_history(
        db, parsed_from, parsed_to, user_id,
    )


@router.get(
    "/{session_id}/activities",
    response_model=list[ActivitySummary],
    summary="Get activity breakdown for a session",
    description="Returns action counts grouped by type for a specific session. SUPER_ADMIN only.",
)
async def get_session_activities(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    return await user_session_service.get_session_activity_summary(db, session_id)


@router.get(
    "/users",
    summary="List users for filter dropdown",
    description="Returns id + full_name of all users. SUPER_ADMIN only.",
)
async def list_users_for_filter(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_super_admin_only),
):
    result = await db.execute(
        select(User.id, User.full_name, User.username, User.role)
        .where(User.is_active == True)
        .order_by(User.full_name)
    )
    return [
        {
            "id": str(row.id),
            "full_name": row.full_name,
            "username": row.username,
            "role": row.role.value if hasattr(row.role, "value") else row.role,
        }
        for row in result.all()
    ]
