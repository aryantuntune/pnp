import asyncio
import datetime
import json
import logging

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db, AsyncSessionLocal
from app.dependencies import require_roles
from app.core.rbac import UserRole
from app.models.user import User
from app.schemas.dashboard import TodaySummaryResponse
from app.services.dashboard_service import get_dashboard_stats, get_today_summary

logger = logging.getLogger("ssmspl")

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/stats",
    summary="Get dashboard statistics",
    description="Returns aggregated dashboard stats: ticket count, today's revenue, active ferries, active branches.",
)
async def stats(
    for_date: datetime.date | None = Query(None, alias="date"),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
            UserRole.BILLING_OPERATOR,
            UserRole.TICKET_CHECKER,
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_stats(db, current_user, for_date=for_date)


@router.get(
    "/today-summary",
    response_model=TodaySummaryResponse,
    summary="Get today's ticket summary",
    description="Returns today's ticket count and revenue broken down by branch and payment mode.",
)
async def today_summary(
    for_date: datetime.date | None = Query(None, alias="date"),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN,
            UserRole.MANAGER,
        )
    ),
    db: AsyncSession = Depends(get_db),
):
    return await get_today_summary(db, current_user, for_date=for_date)


async def _authenticate_ws(websocket: WebSocket) -> tuple[User | None, str | None]:
    """Authenticate a WebSocket connection via cookie or query param token.
    Returns (user, session_id) or (None, None)."""
    # Try cookie first (sent automatically with upgrade request)
    token = websocket.cookies.get("ssmspl_access_token")
    # Fall back to query param for clients that can't send cookies
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        return None, None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None, None
        user_id = payload.get("sub")
        sid = payload.get("sid")
        if not user_id or not sid:
            return None, None
    except JWTError:
        return None, None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            return None, None
        if user.active_session_id != sid:
            return None, None
        return user, sid


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket):
    user, sid = await _authenticate_ws(websocket)
    if user is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    try:
        while True:
            async with AsyncSessionLocal() as db:
                # Re-verify session is still active (handles logout / login elsewhere)
                result = await db.execute(select(User).where(User.id == user.id))
                fresh_user = result.scalar_one_or_none()
                if not fresh_user or fresh_user.active_session_id != sid:
                    await websocket.close(code=4001, reason="Session ended")
                    return
                # Keep session alive
                from datetime import datetime, timezone
                fresh_user.session_last_active = datetime.now(timezone.utc)
                data = await get_dashboard_stats(db, fresh_user)
                await db.commit()
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("Dashboard WebSocket closed for user %s", user.id)
