import uuid
from datetime import date, time, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.rate_change_log import RateChangeLog
from app.models.item import Item
from app.models.route import Route
from app.models.branch import Branch
from app.models.user import User
from app.core.rbac import UserRole


async def _get_route_display_name(db: AsyncSession, route_id: int) -> str | None:
    BranchOne = Branch.__table__.alias("b1")
    BranchTwo = Branch.__table__.alias("b2")
    result = await db.execute(
        select(
            BranchOne.c.name.label("branch_one_name"),
            BranchTwo.c.name.label("branch_two_name"),
        )
        .select_from(Route.__table__)
        .join(BranchOne, BranchOne.c.id == Route.branch_id_one)
        .join(BranchTwo, BranchTwo.c.id == Route.branch_id_two)
        .where(Route.id == route_id)
    )
    row = result.one_or_none()
    if not row:
        return None
    return f"{row.branch_one_name} - {row.branch_two_name}"


async def insert_rate_change_log(
    db: AsyncSession,
    route_id: int,
    item_id: int,
    old_rate: float | None,
    new_rate: float | None,
    updated_by_user: uuid.UUID,
) -> None:
    """Insert a rate change log entry. Called from item_rate_service when rate changes."""
    now = datetime.now()
    log = RateChangeLog(
        date=now.date(),
        time=now.time().replace(microsecond=0),
        route_id=route_id,
        item_id=item_id,
        old_rate=old_rate,
        new_rate=new_rate,
        updated_by_user=updated_by_user,
    )
    db.add(log)


async def get_rate_change_logs(
    db: AsyncSession,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
    date_from: date | None = None,
    date_to: date | None = None,
    route_filter: int | None = None,
    item_filter: int | None = None,
) -> list[dict]:
    """Fetch rate change logs with role-based filtering."""
    query = select(RateChangeLog)

    # Role-based filtering
    if current_user.role == UserRole.MANAGER:
        # Manager: can only view their own actions
        query = query.where(RateChangeLog.updated_by_user == current_user.id)
    elif current_user.role == UserRole.ADMIN:
        # Admin: can view logs of managers and their own
        manager_ids_result = await db.execute(
            select(User.id).where(User.role == UserRole.MANAGER)
        )
        manager_ids = [row[0] for row in manager_ids_result.all()]
        allowed_ids = manager_ids + [current_user.id]
        query = query.where(RateChangeLog.updated_by_user.in_(allowed_ids))
    # SUPER_ADMIN: no filter, sees all

    # Optional filters
    if date_from:
        query = query.where(RateChangeLog.date >= date_from)
    if date_to:
        query = query.where(RateChangeLog.date <= date_to)
    if route_filter:
        query = query.where(RateChangeLog.route_id == route_filter)
    if item_filter:
        query = query.where(RateChangeLog.item_id == item_filter)

    query = query.order_by(RateChangeLog.id.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()

    enriched = []
    for log in rows:
        # Get item name
        item_name = None
        if log.item_id:
            res = await db.execute(select(Item.name).where(Item.id == log.item_id))
            item_name = res.scalar_one_or_none()

        # Get route name
        route_name = None
        if log.route_id:
            route_name = await _get_route_display_name(db, log.route_id)

        # Get user name
        updated_by_name = None
        if log.updated_by_user:
            res = await db.execute(select(User.full_name).where(User.id == log.updated_by_user))
            updated_by_name = res.scalar_one_or_none()

        enriched.append({
            "id": log.id,
            "date": log.date,
            "time": log.time,
            "route_id": log.route_id,
            "item_id": log.item_id,
            "old_rate": float(log.old_rate) if log.old_rate is not None else None,
            "new_rate": float(log.new_rate) if log.new_rate is not None else None,
            "updated_by_user": str(log.updated_by_user),
            "updated_by_name": updated_by_name,
            "item_name": item_name,
            "route_name": route_name,
            "created_at": log.created_at,
        })
    return enriched


async def count_rate_change_logs(
    db: AsyncSession,
    current_user: User,
    date_from: date | None = None,
    date_to: date | None = None,
    route_filter: int | None = None,
    item_filter: int | None = None,
) -> int:
    """Count rate change logs with role-based filtering."""
    query = select(func.count()).select_from(RateChangeLog)

    if current_user.role == UserRole.MANAGER:
        query = query.where(RateChangeLog.updated_by_user == current_user.id)
    elif current_user.role == UserRole.ADMIN:
        manager_ids_result = await db.execute(
            select(User.id).where(User.role == UserRole.MANAGER)
        )
        manager_ids = [row[0] for row in manager_ids_result.all()]
        allowed_ids = manager_ids + [current_user.id]
        query = query.where(RateChangeLog.updated_by_user.in_(allowed_ids))

    if date_from:
        query = query.where(RateChangeLog.date >= date_from)
    if date_to:
        query = query.where(RateChangeLog.date <= date_to)
    if route_filter:
        query = query.where(RateChangeLog.route_id == route_filter)
    if item_filter:
        query = query.where(RateChangeLog.item_id == item_filter)

    result = await db.execute(query)
    return result.scalar()
