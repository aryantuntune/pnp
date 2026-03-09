"""Shared helpers for route-based access scoping.

SUPER_ADMIN and ADMIN see everything (no filtering).
MANAGER, BILLING_OPERATOR, and TICKET_CHECKER are scoped to their assigned
route and that route's two branches.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import UserRole
from app.models.route import Route
from app.models.user import User

# Roles that bypass route scoping
GLOBAL_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN}


def needs_route_scope(user: User) -> bool:
    """Return True if the user's data access should be limited to their route."""
    return user.role not in GLOBAL_ROLES


async def get_route_branch_ids(db: AsyncSession, route_id: int) -> tuple[int, int]:
    """Get both branch IDs for a route.

    Returns (0, 0) if the route does not exist.
    """
    result = await db.execute(
        select(Route.branch_id_one, Route.branch_id_two).where(Route.id == route_id)
    )
    row = result.one_or_none()
    if not row:
        return (0, 0)
    return (row[0], row[1])
