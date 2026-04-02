"""Hide pre-April 2026 ticket data from non-SUPER_ADMIN users.

The system went live in March 2026 but real production data started
April 1, 2026.  All March data is hidden for every role except
SUPER_ADMIN.
"""

import datetime

from app.core.rbac import UserRole

DATA_CUTOFF_DATE = datetime.date(2026, 4, 1)


def clamp_date_from(d: datetime.date | None, user_role: str) -> datetime.date | None:
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        return DATA_CUTOFF_DATE
    return d


def clamp_date_to(d: datetime.date | None, user_role: str) -> datetime.date | None:
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        # Push date_to before cutoff so from > to → empty results
        return DATA_CUTOFF_DATE - datetime.timedelta(days=1)
    return d


def clamp_single_date(d: datetime.date | None, user_role: str) -> datetime.date | None:
    if user_role == UserRole.SUPER_ADMIN:
        return d
    if d is not None and d < DATA_CUTOFF_DATE:
        return DATA_CUTOFF_DATE
    return d


def is_before_cutoff(d: datetime.date | None, user_role: str) -> bool:
    """Return True when a non-SUPER_ADMIN tries to access a date before cutoff."""
    if user_role == UserRole.SUPER_ADMIN:
        return False
    return d is not None and d < DATA_CUTOFF_DATE
