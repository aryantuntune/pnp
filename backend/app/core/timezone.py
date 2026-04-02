"""Timezone-aware date helpers.

The server runs in UTC, but the business operates in IST (UTC+5:30).
All date-based queries (ticket_date, dashboard stats, billing operator
date locking) must use IST so that "today" matches what the operators
see on their wall clock.
"""

from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))


def today_ist() -> date:
    """Return the current date in IST."""
    return datetime.now(IST).date()
